import json
import boto3
from moto import mock_aws
from handler import query_trades_lambda


@mock_aws
def test_query_trades_lambda():
    s3 = boto3.client('s3', region_name='us-west-2')
    s3.create_bucket(Bucket='crypto-trades-bucket', CreateBucketConfiguration={'LocationConstraint': 'us-west-2'})

    dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
    table = dynamodb.create_table(
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

    with table.batch_writer() as batch:
        batch.put_item(Item={
            "Exchange": "binance",
            "Date": "01062024",
            "Pair": "btcusdt",
            "TradeID": "1",
            "Price": "0.1",
            "Qty": "1.0",
            "QuoteQty": "0.1",
            "Time": "123456789",
            "IsBuyerMaker": True,
            "IsBestMatch": True,
        })
        batch.put_item(Item={
            "Exchange": "binance",
            "Date": "01062024",
            "Pair": "ethusdt",
            "TradeID": "2",
            "Price": "0.2",
            "Qty": "2.0",
            "QuoteQty": "0.4",
            "Time": "123456790",
            "IsBuyerMaker": False,
            "IsBestMatch": True,
        })

    event = {
        "queryStringParameters": {
            "exchange": "binance",
            "date": "01062024",
            "pair": "btcusdt"
        }
    }
    context = {}

    result = query_trades_lambda(event, context)

    assert result["statusCode"] == 200
    trades = json.loads(result["body"])
    assert len(trades) == 1
    assert trades[0]["Exchange"] == "binance"
    assert trades[0]["Date"] == "01062024"
    assert trades[0]["Pair"] == "btcusdt"
    assert trades[0]["TradeID"] == "1"