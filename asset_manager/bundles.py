from __future__ import with_statement
from __future__ import unicode_literals

import math
import os
import shutil
import subprocess
import re
import json

from asset_manager.bin_packing import Box, pack_boxes
from asset_manager.datauris import add_data_uris_to_css_file


class InvalidBundleType(Exception):

    def __init__(self, type_):
        msg = "Invalid bundle type: %r" % type_
        super(InvalidBundleType, self).__init__(msg)


class InvalidHtmlPrintableType(Exception):

    def __init__(self, type_):
        msg = "Invalid html printable type: %r" % type_
        super(InvalidHtmlPrintableType, self).__init__(msg)


def png_bundled_first(bundle):
    return 0 if bundle.type == 'image' else 1


def concatenate_files(paths):
    """Generate the contents of several files in 8K blocks."""
    for path in paths:
        with open(path) as input:
            buffer = input.read(8192)
            while buffer:
                yield buffer
                buffer = input.read(8192)


class AssetManager(object):

    def __init__(self, file_name, print_minified=False, domain=''):
        self.bundles = AssetManager._build_bundles_from_config(file_name)
        self.print_minified = print_minified
        self.domain = domain

    def get(self, key):
        return self.bundles.get(key)

    def get_html(self, key, print_source=False):
        return self.bundles.get(key).get_html(self.print_minified,
                                              self.domain,
                                              print_source)

    def minify_all(self):
        for bundle in sorted(self.bundles.values(), key=png_bundled_first):
            bundle.minify()

    @classmethod
    def _build_bundles_from_config(cls, file_name):
        bundles = {}
        with open(file_name, 'r') as file:
            directory = os.path.abspath(os.path.dirname(file_name))
            dict_bundles = json.loads(file.read())
            for key, bundle in dict_bundles.items():
                bundle['path_base'] = os.path.join(directory,
                                                   bundle['path_base'])
                css_path_base = bundle.get('css_path_base')
                if css_path_base:
                    bundle['css_path_base'] = \
                        os.path.join(directory, bundle['css_path_base'])
                bundles[key] = Bundle.from_dict(bundle)
        return bundles


class Bundle(object):

    """Base class for a bundle of media files.

    A bundle is a collection of related static files that can be concatenated
    together and served as a single file to improve performance.
    """

    def __init__(self, file_name, path_base, url_base, files):
        self.file_name = file_name
        self.path_base = path_base
        self.url_base = url_base
        if not url_base.endswith("/"):
            raise ValueError("Bundle URLs must end with a '/'.")
        self.files = self.parse_files(files, path_base)

    @property
    def full_path_files(self):
        return [os.path.join(self.path_base, f) for f in self.files]

    def parse_files(self, files, path_base):
        new_files = []
        for file in files:
            # add all files in directory
            path = os.path.join(path_base, file)
            if os.path.isdir(path):
                if not file.endswith("/"):
                    raise ValueError("Bundle URLs must end with a '/'.")
                for new_file in os.listdir(path):
                    new_files.append(file + new_file)
            else:
                new_files.append(file)
        return tuple(new_files)


    @classmethod
    def check_attr(cls, attrs, attr):
        errmsg = "Invalid bundle: %r attribute %r required." % (attrs, attr)
        assert attr in attrs, errmsg

    @classmethod
    def from_dict(cls, attrs):
        for attr in ("type", "file_name", "path_base", "url_base", "files"):
            cls.check_attr(attrs, attr)

        if attrs["type"] == "js":
            return JavascriptBundle(attrs["file_name"],
                                    attrs["path_base"],
                                    attrs["url_base"],
                                    attrs["files"], 
                                    attrs.get("externs", None))
        elif attrs["type"] == "css":
            return CssBundle(attrs["file_name"],
                             attrs["path_base"],
                             attrs["url_base"],
                             attrs["files"], 
                             attrs.get("data_uri_images", False))
        elif attrs["type"] == "image":
            cls.check_attr(attrs, "css_file_name")
            cls.check_attr(attrs, "css_path_base")
            cls.check_attr(attrs, "css_url_base")
            return PngSpriteBundle(attrs["file_name"],
                                   attrs["path_base"],
                                   attrs["url_base"],
                                   attrs["css_url_base"],
                                   attrs["files"], 
                                   attrs["css_file_name"],
                                   attrs["css_path_base"],
                                   attrs.get("sprite_prefix", "sprite"))
        else:
            raise InvalidBundleType(attrs["type"])

    @property
    def bundle_path(self):
        return os.path.join(self.path_base, self.file_name)

    def make_url(self, file_name, domain=''):
        return domain + self.url_base + file_name

    @property
    def bundle_url(self):
        return self.make_url(self.file_name)

    @property
    def _html_source_template(self):
        raise InvalidHtmlPrintableType

    @property
    def _html_template(self):
        raise InvalidHtmlPrintableType

    def get_html(self, print_minified, domain, print_source):
        elements = []
        if print_source:
            if print_minified:
                files = [self.bundle_path]
            else:
                files = self.full_path_files
            for file in files:
                with open(file) as f:
                    file_contents = f.read()
                    elements.append(
                        self._html_source_template.format(src=file_contents))
        else:
            if print_minified:
                files = [self.make_url(self.file_name, domain)]
            else:
                files = [self.make_url(f, domain) for f in self.files]
            for file in files:
                elements.append(self._html_template.format(url=file))
        return ''.join(elements)


class JavascriptBundle(Bundle):

    """Bundle for JavaScript."""

    def __init__(self, file_name, path_base, url_base, files, externs):
        super(JavascriptBundle, self).__init__(file_name,
                                               path_base,
                                               url_base,
                                               files)
        self.externs = self.parse_files(externs, path) if externs else None

    @property
    def type(self):
        return u'js'

    def get_externs(self):
        return [os.path.join(self.path, f) for f in self.externs]

    @property
    def _minify_command(self):
        command = 'java -jar %s --js_output_file %s' % (
                os.path.join(os.path.dirname(__file__),
                             'bin',
                             'compiler.jar'),
                self.bundle_path,
        )
        for file in self.full_path_files:
            command = '%s --js %s' % (command, file)
        if self.externs:
            for extern in self.get_externs():
                command = '%s --externs %s' % (command, extern)
        return command

    def minify(self):
        os.system(self._minify_command)

    @property
    def _html_template(self):
        return '<script type="text/javascript" src="{url}"></script>'

    @property
    def _html_source_template(self):
        return '<script type="text/javascript">/* <![CDATA[ */{src}/* ]]> */' \
               '</script>'


class CssBundle(Bundle):

    """Bundle for CSS."""

    def __init__(self, file_name, path_base, url_base, files, data_uri_images):
        super(CssBundle, self).__init__(file_name,
                                        path_base,
                                        url_base,
                                        files)
        self.data_uri_images = data_uri_images

    @property
    def type(self):
        return u'css'

    @property
    def _tmp_path(self):
        return '%s.tmp' % self.bundle_path

    @property
    def _minify_command(self):
        return 'java -jar {yui_path} --type css -o {css_path} {tmp_path}' \
            .format(yui_path=os.path.join(os.path.dirname(__file__),
                                          'bin',
                                          'yuicompressor-2.4.2.jar'),
                    css_path=self.bundle_path,
                    tmp_path=self._tmp_path)

    def minify(self):
        # YUI Compressor doesn't combine files, so we do that here
        with open(self._tmp_path, "w") as output:
            generator = concatenate_files(self.full_path_files)
            output.write("".join(generator))
        # Convert image includes to data uri's prior to optimization
        if self.data_uri_images:
            add_data_uris_to_css_file(self._tmp_path)
        # Then we optimize the file
        os.system(self._minify_command)
        os.remove(self._tmp_path)

    @property
    def _html_template(self):
        return '<link rel="stylesheet" type="text/css" href="{url}">'

    @property
    def _html_source_template(self):
        return '<style type="text/css">{src}</style>'


class PngSpriteBundle(Bundle):

    """Bundle for PNG sprites.

    In addition to generating a PNG sprite, it also generates CSS rules so that
    the user can easily place their sprites.  We build sprite bundles before CSS
    bundles so that the user can bundle the generated CSS with the rest of their
    CSS.
    """

    def __init__(self, file_name, path_base, url_base, css_url_base, files,
                 css_file_name, css_path_base, sprite_prefix):
        super(PngSpriteBundle, self).__init__(file_name,
                                              path_base,
                                              url_base,
                                              files)
        self.css_file_name = css_file_name
        self.css_path_base = css_path_base
        self.css_url_base = css_url_base
        self.sprite_prefix = sprite_prefix

    @property
    def type(self):
        return 'image'

    @property
    def css_path(self):
        return os.path.join(self.css_path_base, self.css_file_name)

    def minify(self):
        import Image  # If this fails, you need the Python Imaging Library.
        boxes = [ImageBox(Image.open(path), path) for path in self.full_path_files]
        # Pick a max_width so that the sprite is squarish and a multiple of 16,
        # and so no image is too wide to fit.
        total_area = sum(box.width * box.height for box in boxes)
        width = max(max(box.width for box in boxes),
                    (int(math.sqrt(total_area)) // 16 + 1) * 16)
        (_, height, packing) = pack_boxes(boxes, width)
        sprite = Image.new( mode='RGBA',
                            size=(width, height),
                            color=(0,0,0,0))
        for (left, top, box) in packing:
            # This is a bit of magic to make the transparencies work.  To
            # preserve transparency, we pass the image so it can take its
            # alpha channel mask or something.  However, if the image has no
            # alpha channels, then it fails, we we have to check if the
            # image is RGBA here.
            img = box.image
            sprite.paste(img, (left, top))
        sprite.save(self.bundle_path, "PNG")
        self._optimize_output()
        self.generate_css(packing)

    def _optimize_output(self):
        """Optimize the PNG with pngcrush."""
        sprite_path = self.bundle_path
        tmp_path = sprite_path + '.tmp'
        try:
            args = ['pngcrush', '-rem', 'alla', sprite_path, tmp_path]
            proc = subprocess.Popen(args, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)
            proc.wait()
            if proc.returncode != 0:
                raise Exception('pngcrush returned error code: %r\nOutput was:\n\n'
                                '%s' % (proc.returncode, proc.stdout.read()))
        except OSError:
            pass
        shutil.move(tmp_path, sprite_path)

    def generate_css(self, packing):
        """Generate the background offset CSS rules."""
        with open(self.css_path, "w") as css:
            css.write("/* Generated classes for sprites.  "
                      "Don't edit! */\n")
            props = {
                "background-image": "url('%s')" % self.bundle_url,
            }
            css.write(self.make_css(None, props))
            for (left, top, box) in packing:
                props = {
                    "background-position": "%dpx %dpx" % (-left, -top),
                    "width": "%dpx" % box.width,
                    "height": "%dpx" % box.height,
                }
                css.write(self.make_css(os.path.basename(box.filename), props))

    CSS_REGEXP = re.compile(r"[^a-zA-Z0-9\-_]")

    def css_class_name(self, rule_name):
        name = self.sprite_prefix
        if rule_name:
            name += "-" + rule_name
        name = name.replace(" ", "-").replace('.png','').replace('_','-').replace(".", "-")
        return self.CSS_REGEXP.sub("", name)

    def make_css(self, name, props):
        # We try to format it nicely here in case the user actually looks at it.
        # If he wants it small, he'll bundle it up in his CssBundle.
        css_class = self.css_class_name(name)
        css_propstr = "".join("     %s: %s;\n" % p for p in props.iteritems())
        return "\n.%s {\n%s}\n" % (css_class, css_propstr)


class ImageBox(Box):

    """A Box representing an image.

    We hand these off to the bin packing algorithm.  After the boxes have been
    arranged, we can place the associated image in the sprite.
    """

    def __init__(self, image, filename):
        (width, height) = image.size
        super(ImageBox, self).__init__(width, height)
        self.image = image
        self.filename = filename

    def __repr__(self):
        return "<ImageBox: filename=%r image=%r>" % (self.filename, self.image)

