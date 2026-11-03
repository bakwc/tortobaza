import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image
from rest_framework.test import APIClient


class ImageCropTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        buf = io.BytesIO()
        im = Image.new("RGB", (800, 400))
        for x in range(800):
            for y in range(400):
                im.putpixel((x, y), (x % 256, y % 256, (x + y) % 256))
        im.save(buf, format="JPEG")
        buf.seek(0)
        self.upload = SimpleUploadedFile("wide.jpg", buf.read(), content_type="image/jpeg")

    def _save_product_image(self) -> str:
        from catalog.models import Category, Product, ProductImage

        category = Category.objects.create(name="Test", slug="test-crop")
        product = Product.objects.create(
            category=category,
            name="Crop product",
            slug="crop-product",
            base_price="10.00",
        )
        row = ProductImage.objects.create(product=product, image=self.upload)
        return row.image.name

    def test_invalid_crop_returns_400(self):
        rel = self._save_product_image()
        bad = self.client.get(f"/api/img/{rel}?w=400&crop=2,0,1")
        self.assertEqual(bad.status_code, 400)

    def test_cropped_output_is_square_after_scale(self):
        rel = self._save_product_image()
        resp = self.client.get(f"/api/img/{rel}?w=400&crop=0,0,1")
        self.assertEqual(resp.status_code, 200)
        body = b"".join(resp.streaming_content)
        im = Image.open(io.BytesIO(body))
        self.assertEqual(im.size[0], 400)
        self.assertEqual(im.size[1], 400)

    def test_different_crop_uses_different_cache(self):
        rel = self._save_product_image()
        first = self.client.get(f"/api/img/{rel}?w=200&crop=0,0,1")
        second = self.client.get(f"/api/img/{rel}?w=200&crop=0.5,0,0.5")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertNotEqual(b"".join(first.streaming_content), b"".join(second.streaming_content))
