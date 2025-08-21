import tempfile

import qrcode
import qrcode.image.svg


def generate_qrcode(content):
    f = tempfile.NamedTemporaryFile(suffix=".svg", delete=True)

    factory = qrcode.image.svg.SvgImage

    qr = qrcode.QRCode(
        image_factory=factory,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        version=None,
        border=0,
    )
    qr.add_data(content)
    i = qr.make_image()
    i.save(f)

    return f
