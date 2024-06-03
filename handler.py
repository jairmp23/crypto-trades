import json
import boto3
import pandas as pd
from datetime import datetime
from io import StringIO
from utils.fetch_trades import (
    fetch_trades_binance,
    fetch_trades_coinbase,
    fetch_trades_kraken,
)

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("CryptoTrades")

EXCHANGES = ["binance", "coinbase", "kraken"]
PAIRS = ["btcusdt", "ethusdt"]

EXCHANGE_FUNCTIONS = {
    "binance": fetch_trades_binance,
    "coinbase": fetch_trades_coinbase,
    "kraken": fetch_trades_kraken,
}


def get_trades(exchange, pair):
    fetch_function = EXCHANGE_FUNCTIONS.get(exchange)
    if fetch_function:
        return fetch_function(pair)
    else:
        return []


def fetch_trades_lambda(event, context):
    now = datetime.now()
    date_str = now.strftime("%d%m%Y")

    for exchange in EXCHANGES:
        all_trades = []
        for pair in PAIRS:
            trades = get_trades(exchange, pair)
            for trade in trades:
                trade["pair"] = pair
                all_trades.append(trade)

        df = pd.DataFrame(all_trades)
        df["exchange"] = exchange
        df["date"] = date_str

        file_name = f"{exchange}_{date_str}.csv"
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)

        s3.put_object(
            Bucket="crypto-trades-bucket",
            Key=f"{exchange}/{file_name}",
            Body=csv_buffer.getvalue(),
        )

    return {
        "statusCode": 200,
        "body": json.dumps("Trades fetched and stored successfully!"),
    }


def process_trades_lambda(event, context):

    bucket = event["Records"][0]["s3"]["bucket"]["name"]
    key = event["Records"][0]["s3"]["object"]["key"]
    exchange = key.split("/")[0]
    date_str = key.split("_")[1].split(".")[0]

    obj = s3.get_object(Bucket=bucket, Key=key)
    csv_content = obj["Body"].read().decode("utf-8")

    df = pd.read_csv(StringIO(csv_content))

    with table.batch_writer() as batch:
        for _, row in df.iterrows():
            batch.put_item(
                Item={
                    "Exchange": str(exchange),
                    "Date": date_str,
                    "TradeID": str(row["id"]),
                    "Pair": str(row["pair"]),
                    "Price": str(row["price"]),
                    "Qty": str(row["qty"]),
                    "QuoteQty": str(row["quoteQty"]),
                    "Time": str(row["time"]),
                    "IsBuyerMaker": row["isBuyerMaker"],
                    "IsBestMatch": row["isBestMatch"],
                }
            )

    return {
        "statusCode": 200,
        "body": json.dumps("Trades inserted into DynamoDB successfully!"),
    }


def query_trades_lambda(event, context):

    params = event["queryStringParameters"]
    exchange = params.get("exchange")
    date = params.get("date")
    pair = params.get("pair")

    filter_expression = []
    expression_attribute_names = {}
    expression_attribute_values = {}

    if exchange:
        filter_expression.append("#exchange = :exchange")
        expression_attribute_names["#exchange"] = "Exchange"
        expression_attribute_values[":exchange"] = exchange

    if date:
        filter_expression.append("#date = :date")
        expression_attribute_names["#date"] = "Date"
        expression_attribute_values[":date"] = date

    if pair:
        filter_expression.append("Pair = :pair")
        expression_attribute_values[":pair"] = pair

    if filter_expression:
        filter_expression = " AND ".join(filter_expression)
    else:
        filter_expression = "attribute_exists(Exchange)"

    response = table.scan(
        FilterExpression=filter_expression,
        ExpressionAttributeNames=expression_attribute_names,
        ExpressionAttributeValues=expression_attribute_values,
    )

    trades = response["Items"]

    return {
        "statusCode": 200,
        "body": json.dumps(trades),
        "headers": {
            "Content-Type": "application/json",
        },
    }
