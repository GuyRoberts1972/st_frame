import unittest
import boto3
import json

class TestLangChainUtils(unittest.TestCase):

    def test_bedrock_invocation(self):
        ''' test we can get a basic reponse back from a typical model '''
        
        prompt = "Tell me a short story"
        bedrock_runtime = boto3.client('bedrock-runtime')
        model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 500,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "top_p": 1
        })

        response = bedrock_runtime.invoke_model(
            body=body,
            modelId=model_id,
            accept='application/json',
            contentType='application/json'
        )

        response_body = json.loads(response.get('body').read())
        text = response_body.get('content')[0]['text']
        self.assertTrue(10 < len(text))

if __name__ == "__main__":
    unittest.main()

