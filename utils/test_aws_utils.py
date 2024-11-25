# pylint: disable=missing-function-docstring, missing-module-docstring, missing-class-docstring, protected-access
import unittest
from unittest.mock import patch
from utils.aws_utils import AWSUtils


class TestAWSUtils(unittest.TestCase):

    @patch("utils.aws_utils.boto3.Session")
    def test_aws_not_configured(self, mock_session):
        """
        Test when AWS credentials and region are not configured.
        """
        mock_session.return_value.get_credentials.return_value = None
        mock_session.return_value.region_name = None

        success, reason = AWSUtils.is_aws_configured()
        self.assertFalse(success)
        self.assertEqual(reason, AWSUtils.CREDENTIALS_NOT_CONFIGURED)

    @patch("utils.aws_utils.boto3.Session")
    def test_aws_no_region(self, mock_session):
        """
        Test when AWS credentials are configured, but region is missing.
        """
        class MockCredentials: #pylint: disable=too-few-public-methods
            access_key = "ABCD1234"
            secret_key = "secret"

        mock_session.return_value.get_credentials.return_value = MockCredentials()
        mock_session.return_value.region_name = None

        success, reason = AWSUtils.is_aws_configured()
        self.assertFalse(success)
        self.assertEqual(reason, AWSUtils.REGION_NOT_CONFIGURED)

    @patch("utils.aws_utils.boto3.Session")
    def test_aws_configured(self, mock_session):
        """
        Test when AWS credentials and region are configured correctly.
        """
        class MockCredentials: #pylint: disable=too-few-public-methods
            access_key = "ABCD1234"
            secret_key = "secret"

        mock_session.return_value.get_credentials.return_value = MockCredentials()
        mock_session.return_value.region_name = "us-east-1"

        success, reason = AWSUtils.is_aws_configured()
        self.assertTrue(success)
        self.assertEqual(
            reason, AWSUtils.CONFIGURED.format(region="us-east-1", access_key="ABCD")
        )

    @patch("utils.aws_utils.boto3.Session")
    def test_partial_credentials(self, mock_session):
        """
        Test when AWS credentials are partially configured.
        """
        class MockCredentials: #pylint: disable=too-few-public-methods
            access_key = None
            secret_key = "secret"

        mock_session.return_value.get_credentials.return_value = MockCredentials()
        mock_session.return_value.region_name = "us-east-1"

        success, reason = AWSUtils.is_aws_configured()
        self.assertFalse(success)
        self.assertEqual(reason, AWSUtils.PARTIAL_CREDENTIALS)


if __name__ == "__main__":
    unittest.main()
