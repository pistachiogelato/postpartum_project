from django.test import TestCase
from .utils import validate_image_url
from .models import FamilyArtDaily
from django.utils import timezone

class ImageUrlTests(TestCase):
    """Test cases for image URL validation and storage"""
    
    def setUp(self):
        """Set up test data"""
        self.valid_image_url = "https://i.imgur.com/M0p4iuQ.jpg"
        self.invalid_image_url = "https://example.com/my_document.txt" 
        
        # Create test art entry
        self.art_entry = FamilyArtDaily.objects.create(
            family_name="test_family",
            keywords=["happy", "sunny", "peaceful"],
            date=timezone.now().date()
        )
    
    def test_url_validation(self):
        """Test URL validation function"""
        # Test valid URL
        is_valid, error = validate_image_url(self.valid_image_url)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        # Test invalid URL
        is_valid, error = validate_image_url(self.invalid_image_url)
        self.assertFalse(is_valid)
        self.assertIsNotNone(error)
    
    def test_url_storage(self):
        """Test URL storage in database"""
        # Save URL
        self.art_entry.image_url = self.valid_image_url
        self.art_entry.save()
        
        # Retrieve and verify
        saved_entry = FamilyArtDaily.objects.get(id=self.art_entry.id)
        self.assertEqual(saved_entry.image_url, self.valid_image_url)
