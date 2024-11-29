""" Helpers for AWS """
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, NoRegionError


class AWSUtils:
    """ Class for genetal AWS utilities """

    # String constants
    CREDENTIALS_NOT_CONFIGURED = "AWS credentials are not configured."
    REGION_NOT_CONFIGURED = "AWS region is not configured."
    PARTIAL_CREDENTIALS = "AWS credentials are partially configured. Check your setup."
    CONFIGURED = "Ok, {region}, Key: {access_key}****"
    UNEXPECTED_ERROR = "An unexpected error occurred: {error}"

    @staticmethod
    def is_aws_configured() -> tuple[bool, str]:
        """
        Checks if AWS is configured by validating credentials and default region.
        Returns a tuple (Y/N, status)
        """
        try:
            session = boto3.Session()
            credentials = session.get_credentials()
            if credentials is None:
                return False, AWSUtils.CREDENTIALS_NOT_CONFIGURED

             # Validate credentials
            access_key = credentials.access_key
            secret_key = credentials.secret_key
            if not access_key or not secret_key:
                return False, AWSUtils.PARTIAL_CREDENTIALS


            region = session.region_name
            if not region:
                return False, AWSUtils.REGION_NOT_CONFIGURED

            return True, AWSUtils.CONFIGURED.format(
                region=region, access_key=credentials.access_key[:4]
            )


        except NoCredentialsError:
            return False, AWSUtils.CREDENTIALS_NOT_CONFIGURED
        except PartialCredentialsError:
            return False, AWSUtils.PARTIAL_CREDENTIALS
        except NoRegionError:
            return False, AWSUtils.REGION_NOT_CONFIGURED
        except Exception as e: #pylint: disable = broad-exception-caught
            return False, AWSUtils.UNEXPECTED_ERROR.format(error=str(e))