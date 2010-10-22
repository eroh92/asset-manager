import os.path
import unittest
import os

from asset_manager import bundles
from asset_manager.bundles import AssetManager
from asset_manager.bundles import JavascriptBundle
from asset_manager.bundles import CssBundle
from asset_manager.bundles import PngSpriteBundle

setup_path = os.path.abspath(os.path.dirname(__file__))
json_setup_path = os.path.join(setup_path, 'example_setup.json')


def _remove_static_file(directory, file):
    try:
        os.remove(os.path.join(setup_path, directory, file))
    except OSError:
        # Don't want removing of files to cause further test errors
        # to add white noise to testing
        pass
    except IOError:
        # Ditto
        pass


def _remove_static_files():
    _remove_static_file('testcss', 'bundle.min.css')
    _remove_static_file('testcss', 'bundle2.min.css')
    _remove_static_file('testcss', 'bundle3.min.css')
    _remove_static_file('testcss', 'sprite.css')
    _remove_static_file('testcss', 'sprite2.css')
    _remove_static_file('testjs', 'bundle.min.js')
    _remove_static_file('testimg', 'sprite.png')
    _remove_static_file('testimg', 'sprite2.png')


class TestBundles(unittest.TestCase):

    def setUp(self):
        self.setup_path = setup_path
        self.bundle_manager = AssetManager(json_setup_path)

    @classmethod
    def tearDown(self):
        _remove_static_files()

    def test_css_bundle_built_correctly_from_file(self):
        bundle = self.bundle_manager.get('bundle.css')
        self.assertEqual(type(bundle), CssBundle)
        self.assertEqual(bundle.type, 'css')
        self.assertEqual(bundle.file_name, 'bundle.min.css')
        path_base = os.path.join(self.setup_path, 'testcss')
        self.assertEqual(bundle.path_base, path_base)
        self.assertEqual(bundle.url_base, '/styles/')
        self.assertFalse(bundle.data_uri_images)
        self.assertEqual(bundle.files, ('color.css', 'text.css'))
        self.assertEqual(bundle.full_path_files,
            [os.path.join(path_base, 'color.css'),
             os.path.join(path_base, 'text.css')])
        self.assertEqual(bundle.bundle_path, os.path.join(path_base,
                                                          'bundle.min.css'))
                                                          
        bin_path = os.path.join(os.path.dirname(bundles.__file__), 'bin')
        self.assertEqual(bundle._minify_command,
            'java -jar {bin}{sep}yuicompressor-2.4.2.jar --type css '
            '-o {css_path}{sep}bundle.min.css {css_path}{sep}bundle.min.css.tmp'
            .format(bin=bin_path,
                css_path=path_base,
                sep=os.path.sep))


    def test_js_bundle_built_correctly_from_file(self):
        bundle = self.bundle_manager.get('bundle.js')
        self.assertEqual(type(bundle), JavascriptBundle)
        self.assertEqual(bundle.type, 'js')
        self.assertEqual(bundle.file_name, 'bundle.min.js')
        path_base = os.path.join(self.setup_path, 'testjs')
        self.assertEqual(bundle.path_base, path_base)
        self.assertEqual(bundle.url_base, '/scripts/')
        self.assertEqual(bundle.files, ('page1.js', 'page2.js'))
        self.assertEqual(bundle.full_path_files,
            [os.path.join(path_base, 'page1.js'),
             os.path.join(path_base, 'page2.js')])
        self.assertEqual(bundle.bundle_path, os.path.join(path_base,
                                                          'bundle.min.js'))

        bin_path = os.path.join(os.path.dirname(bundles.__file__), 'bin')
        self.assertEqual(bundle._minify_command,
            'java -jar {bin}{sep}compiler.jar --js_output_file '
            '{js_path}{sep}bundle.min.js --js {js_path}{sep}page1.js --js '
            '{js_path}{sep}page2.js'.format(bin=bin_path,
                                            js_path=path_base,
                                            sep=os.path.sep))

    def test_image_bundle_built_correctly_from_file(self):
        bundle = self.bundle_manager.get('sprite.png')
        self.assertEqual(type(bundle), PngSpriteBundle)
        self.assertEqual(bundle.type, 'image')
        self.assertEqual(bundle.file_name, 'sprite.png')
        path_base = os.path.join(self.setup_path, 'testimg')
        self.assertEqual(bundle.path_base, path_base)
        self.assertEqual(bundle.url_base, '/images/')
        self.assertEqual(bundle.sprite_prefix, 'sprite')
        self.assertEqual(bundle.css_path_base, os.path.join(self.setup_path,
                                                            'testcss'))
        self.assertEqual(bundle.files, ('test1.png', 'test2.png'))
        self.assertEqual(bundle.css_file_name, 'sprite.css')
        self.assertEqual(bundle.full_path_files,
            [os.path.join(path_base, 'test1.png'),
             os.path.join(path_base, 'test2.png')])
        self.assertEqual(bundle.bundle_path, os.path.join(path_base,
                                                          'sprite.png'))

    def test_minify_css(self):
        bundle = self.bundle_manager.get('bundle.css')
        bundle.minify()
        with open(os.path.join(self.setup_path,
                               'testcss',
                               'bundle.min.css'), 'r') as file:
            file_contents = file.read()
            self.assertEqual(file_contents,
                             '.green{color:green;}#nice{color:#fff;}#try{color:'
                             '#fefefe;}#oh{color:#e96;}#my{color:#e96;}h1{'
                             'font-weight:bold;font-weight:normal;}h2.smaller'
                             '{font-size:12px;}')
        # ensure tmp file is removed after minification
        try:
            with open(os.path.join(self.setup_path,
                                   'testcss',
                                   'bundle.min.css.tmp'), 'r') as file:
                pass
            self.assertTrue(False, 'tmp file still exists!')
        except IOError:
            self.assertTrue(True, 'Got an IOError because tmp file is gone')

    def test_minify_css_with_data_uri(self):
        bundle = self.bundle_manager.get('bundle3.css')
        bundle.minify()
        with open(os.path.join(self.setup_path,
                               'testcss',
                               'bundle3.min.css'), 'r') as file:
            file_contents = file.read()
            self.assertEqual(len(file_contents), 7386)
            self.assertEqual(file_contents.count('data:image/png;base64'), 2)
            self.assertEqual(file_contents.count('#try{color:#fefefe;}'), 1)

    def test_minify_js(self):
        bundle = self.bundle_manager.get('bundle.js')
        bundle.minify()
        with open(os.path.join(self.setup_path,
                               'testjs',
                               'bundle.min.js'), 'r') as file:
            file_contents = file.read()
            self.assertEqual(file_contents,
                             'var helloVariable="hello",sayHello=function(){'
                             'alert(helloVariable)};sayHello();(function(){'
                             'alert("hello")})();\n')

    def test_minify_image_in_sub_folders(self):
        bundle = self.bundle_manager.get('sprite2.png')
        bundle.minify()
        with open(os.path.join(self.setup_path,
                               'testimg',
                               'sprite2.png'), 'r') as file:
            file_contents = file.read()
            self.assertEqual(len(file_contents), 4572)

        with open(os.path.join(self.setup_path,
                               'testcss',
                               'sprite2.css'), 'r') as file:
            file_contents = file.read()
            self.assertEqual(file_contents,
                '/* Generated classes for sprites.  Don\'t edit! '
                '*/\n\n.sprite2 {\n     background-image: '
                'url(\'/images/sprite2.png\');\n}\n\n.'
                'sprite2-test2 {\n     width: 50px;\n     '
                'background-position: '
                '0px 0px;\n     height: 60px;\n}\n\n.sprite2-test1 {\n     '
                'width: 20px;\n     background-position: 0px -60px;\n     '
                'height: 25px;\n}\n')

    def test_minify_image(self):
        bundle = self.bundle_manager.get('sprite.png')
        bundle.minify()
        with open(os.path.join(self.setup_path,
                               'testimg',
                               'sprite.png'), 'r') as file:
            file_contents = file.read()
            self.assertEqual(len(file_contents), 4572)

        with open(os.path.join(self.setup_path,
                               'testcss',
                               'sprite.css'), 'r') as file:
            file_contents = file.read()
            self.assertEqual(file_contents,
                '/* Generated classes for sprites.  Don\'t edit! */\n\n.sprite '
                '{\n     background-image: url(\'/images/sprite.png\');\n}\n\n.'
                'sprite-test2 {\n     width: 50px;\n     background-position: '
                '0px 0px;\n     height: 60px;\n}\n\n.sprite-test1 {\n     '
                'width: 20px;\n     background-position: 0px -60px;\n     '
                'height: 25px;\n}\n')

    def test_bundle_all(self):
        # This is here to ensure that test_bundle_all blows up if
        # sprite.css isn't created before the first css bundle
        # Don't remove!
        _remove_static_files()

        self.bundle_manager.minify_all()

        with open(os.path.join(self.setup_path,
                               'testcss',
                               'bundle2.min.css'), 'r') as file:
            file_contents = file.read()
            self.assertEqual(file_contents,
                             '.sprite{background-image:url(\'/images/sprite.png'
                             '\');}.sprite-test2{width:50px;background-position'
                             ':0 0;height:60px;}.sprite-test1{width:20px;backgr'
                             'ound-position:0 -60px;height:25px;}'
                             '.green{color:green;}#nice{color:#fff;}#try{color:'
                             '#fefefe;}#oh{color:#e96;}#my{color:#e96;}h1{'
                             'font-weight:bold;font-weight:normal;}h2.smaller'
                             '{font-size:12px;}')


class TestPrintingHtmlOfBundles(unittest.TestCase):

    def test_source_non_minified(self):
        bundle_manager = AssetManager(json_setup_path,
                                       print_minified=False,
                                       domain='')
        self.assertEqual(bundle_manager.get_html('bundle.css', True),
            '<style type="text/css">/* final shouldn\'t have comments '
            '*/\n.green {\n    color: green; /* here either */\n}\n#nice '
            '{\n    color: #ffffff;\n}\n#try {\n    color: #fefefe;\n}\n#oh '
            '{\n    color: #e96;\n}\n#my {\n    color: '
            '#ee9966;\n}\n\n</style><style type="text/css">h1 {\n    '
            'font-weight: bold;\n    font-weight: normal;\n}\nh2.smaller '
            '{\n    font-size: 12px;\n}</style>')
        self.assertEqual(bundle_manager.get_html('bundle.js', True),
            '<script type="text/javascript">/* <![CDATA[ *//* comments '
            'should be stripped */\nvar helloVariable = \'hello\';\nvar '
            'sayHello = function(removed){\n    /* in the middle */\n    '
            'alert(helloVariable);\n};\nsayHello(); // these should be '
            'too/* ]]> */</script><script type="text/javascript">/* '
            '<![CDATA[ */(function(){\n    /* comments should be stripped '
            '*/\n    var helloVariable = \'hello\';\n    var sayHello = '
            'function(removed){\n        /* in the middle */\n        '
            'alert(helloVariable);\n    };\n    sayHello(); // these '
            'should be too\n})();/* ]]> */</script>')

    def test_source_minified(self):
        bundle_manager = AssetManager(json_setup_path,
                                       print_minified=True,
                                       domain='')

        bundle_manager.get('bundle.css').minify()
        bundle_manager.get('bundle.js').minify()
        
        self.assertEqual(bundle_manager.get_html('bundle.css', True),
            '<style type="text/css">.green{color:green;}#nice{color:#fff;}'
            '#try{color:#fefefe;}#oh{color:#e96;}#my{color:#e96;}h1'
            '{font-weight:bold;font-weight:normal;}h2.smaller'
            '{font-size:12px;}</style>')
        self.assertEqual(bundle_manager.get_html('bundle.js', True),
            '<script type="text/javascript">/* <![CDATA[ */var '
            'helloVariable="hello",sayHello=function(){alert(helloVariable)};'
            'sayHello();(function(){alert("hello")})();\n/* ]]> */</script>')

        _remove_static_files()
            
    def test_no_domain_minified(self):
        bundle_manager = AssetManager(json_setup_path,
                                       print_minified=True,
                                       domain='')
        self.assertEqual(bundle_manager.get_html('bundle2.css'),
            '<link rel="stylesheet" type="text/css" '
            'href="/styles/bundle2.min.css">')
        self.assertEqual(bundle_manager.get_html('bundle.js'),
            '<script type="text/javascript" '
            'src="/scripts/bundle.min.js"></script>')

    def test_domain_minified(self):
        bundle_manager = AssetManager(json_setup_path,
                                       print_minified=True,
                                       domain='http://static.test.com')
        self.assertEqual(bundle_manager.get_html('bundle2.css'),
            '<link rel="stylesheet" type="text/css" '
            'href="http://static.test.com/styles/bundle2.min.css">')
        self.assertEqual(bundle_manager.get_html('bundle.js'),
            '<script type="text/javascript" '
            'src="http://static.test.com/scripts/bundle.min.js"></script>')

    def test_no_domain_not_minified(self):
        bundle_manager = AssetManager(json_setup_path,
                                       print_minified=False,
                                       domain='')
        self.assertEqual(bundle_manager.get_html('bundle2.css'),
            '<link rel="stylesheet" type="text/css" '
            'href="/styles/sprite.css">'
            '<link rel="stylesheet" type="text/css" '
            'href="/styles/color.css">'
            '<link rel="stylesheet" type="text/css" '
            'href="/styles/text.css">')
        self.assertEqual(bundle_manager.get_html('bundle.js'),
            '<script type="text/javascript" '
            'src="/scripts/page1.js"></script>'
            '<script type="text/javascript" '
            'src="/scripts/page2.js"></script>')

    def test_domain_not_minified(self):
        bundle_manager = AssetManager(json_setup_path,
                                       print_minified=False,
                                       domain='http://static.test.com')
        self.assertEqual(bundle_manager.get_html('bundle2.css'),
            '<link rel="stylesheet" type="text/css" '
            'href="http://static.test.com/styles/sprite.css">'
            '<link rel="stylesheet" type="text/css" '
            'href="http://static.test.com/styles/color.css">'
            '<link rel="stylesheet" type="text/css" '
            'href="http://static.test.com/styles/text.css">')
        self.assertEqual(bundle_manager.get_html('bundle.js'),
            '<script type="text/javascript" '
            'src="http://static.test.com/scripts/page1.js"></script>'
            '<script type="text/javascript" '
            'src="http://static.test.com/scripts/page2.js"></script>')


if __name__ == '__main__':
    unittest.main()
