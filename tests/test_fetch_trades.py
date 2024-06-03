import json
import boto3
import requests_mock
from moto import mock_aws
from handler import fetch_trades_lambda


@mock_aws
@requests_mock.Mocker(kw='mock')
def test_fetch_trades(**kwargs):
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

    trades_response = [
        {
            "id": 1,
            "price": "0.1",
            "qty": "1.0",
            "quoteQty": "0.1",
            "time": 123456789,
            "isBuyerMaker": True,
            "isBestMatch": True,
        },
        {
            "id": 2,
            "price": "0.2",
            "qty": "2.0",
            "quoteQty": "0.4",
            "time": 123456790,
            "isBuyerMaker": False,
            "isBestMatch": True,
        },
    ]
    kwargs['mock'].get(
        "https://api.binance.com/api/v3/trades?symbol=BTCUSDT", json=trades_response
    )
    kwargs['mock'].get(
        "https://api.binance.com/api/v3/trades?symbol=ETHUSDT", json=trades_response
    )
    kwargs['mock'].get(
        "https://api.pro.coinbase.com/products/BTCUSDT/trades", json=trades_response
    )
    kwargs['mock'].get(
        "https://api.pro.coinbase.com/products/ETHUSDT/trades", json=trades_response
    )
    kwargs['mock'].get(
        "https://api.kraken.com/0/public/Trades?pair=BTCUSDT", json=trades_response
    )
    kwargs['mock'].get(
        "https://api.kraken.com/0/public/Trades?pair=ETHUSDT", json=trades_response
    )

    event = {}
    context = {}

    result = fetch_trades_lambda(event, context)

    response = s3.list_objects_v2(Bucket="crypto-trades-bucket")

    assert "Contents" in response
    assert len(response["Contents"]) == 3

    assert result["statusCode"] == 200
    assert json.loads(result["body"]) == "Trades fetched and stored successfully!"


