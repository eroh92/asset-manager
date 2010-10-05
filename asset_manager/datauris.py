import base64
import re
import os

URL_FINDER = re.compile('url\(.*?\)')
STRIP_URL = re.compile('url\(|\)|\'|"')

file_extensions_to_types = {
    "png": "image/png",
    "jpg": "image/jpg",
    "gif": "image/gif",
}

def _extract_image_urls_from_css(css):
    return URL_FINDER.findall(css)

def _extract_image_urls_from_css_file(css_path):
    with open(css_path, 'r') as css_file:
        return _extract_image_urls_from_css(css_file.read())

def _get_image_path_from_css_url(css_image_url):
    """
    >>> _get_image_path_from_css_url('url(../test/nice.png)')
    '../test/nice.png'
    >>> _get_image_path_from_css_url('url("../test/nice.png")')
    '../test/nice.png'
    >>> _get_image_path_from_css_url('url(\'../test/nice.png\')')
    '../test/nice.png'
 
    """
    return ''.join(STRIP_URL.split(css_image_url))

def _parse_image_url_into_data_uris(css_path, image_url):
    return convert_file_to_data_uri(os.path.join(
        os.path.dirname(css_path), 
        image_url))

def add_data_uris_to_css_file(css_path):
    css_file_content = ''
    with open(css_path, 'r') as css_file:
        css_file_content = css_file.read()
        image_urls = _extract_image_urls_from_css(css_file_content)
        for css_image_url in image_urls:
            try:
                image_url = _get_image_path_from_css_url(css_image_url)
                data_uri = _parse_image_url_into_data_uris(css_path, image_url)
                css_file_content = css_file_content.replace(image_url, data_uri)
            except KeyError:
                pass
            except IOError:
                pass

    with open(css_path, 'w') as css_file:
        css_file.write(css_file_content)


def _get_file_type(path):
    return file_extensions_to_types[_get_file_extension_from_path(path)]
    
def _get_file_extension_from_path(path):
    """
    >>> _get_file_extension_from_path('/test/nice/png.png')
    "png"
    >>> _get_file_extension_from_path('nice.png')
    "png"
    >>> _get_file_extension_from_path('/nice.JPG')
    "jpg"
    """
    return path.split('.')[-1].lower()

def convert_file_to_data_uri(path):
    with open(path, 'r') as image:
        return 'data:%s;base64,%s' % (
            _get_file_type(path),
            base64.b64encode(image.read()))

