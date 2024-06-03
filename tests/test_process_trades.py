import json
import boto3
from io import StringIO
import pandas as pd
from moto import mock_aws
from handler import process_trades_lambda

@mock_aws
def test_process_trades():
    s3 = boto3.client('s3', region_name='us-west-2')
    s3.create_bucket(
        Bucket='crypto-trades-bucket',
        CreateBucketConfiguration={'LocationConstraint': 'us-west-2'}
    )

    dynamodb = boto3.client("dynamodb", region_name="us-west-2")
    dynamodb.create_table(
        TableName="CryptoTrades",
        KeySchema=[
            {"AttributeName": "Exchange", "KeyType": "HASH"},
            {"AttributeName": "TradeID", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "Exchange", "AttributeType": "S"},
            {"AttributeName": "TradeID", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )

    trades_data = {
        "id": ["1", "2"],
        "price": ["0.1", "0.2"],
        "qty": ["1.0", "2.0"],
        "pair": ["btcusdt", "btcusdt"],
        "quoteQty": ["0.1", "0.4"],
        "time": ["123456789", "123456790"],
        "isBuyerMaker": [True, False],
        "isBestMatch": [True, True],
        "exchange": ["binance", "coinbase"],
        "date": ["01012020", "01012020"],
    }

    df = pd.DataFrame(trades_data)
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)

    s3.put_object(
        Bucket="crypto-trades-bucket",
        Key="binance_01012020.csv",
        Body=csv_buffer.getvalue(),
    )

    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "crypto-trades-bucket"},
                    "object": {"key": "binance_01012020.csv"},
                }
            }
        ]
    }
    context = {}

    result = process_trades_lambda(event, context)

    dynamodb_resource = boto3.resource("dynamodb", region_name="us-west-2")
    table = dynamodb_resource.Table("CryptoTrades")
    response = table.scan()
    items = response["Items"]

    assert items[0]["Exchange"] == "binance_01012020.csv"
    assert items[0]["TradeID"] == "1"

    assert result["statusCode"] == 200
    assert json.loads(result["body"]) == "Trades inserted into DynamoDB successfully!"
