# bitcoin-price-alert
A bitmex companion tool, akin to using subscription-only price alerts on TradingView. 
Capabilities:
* track price movement from current position;
* set alarms on price preference;


## Usage
* get an alert when price exceeds 10000 - `/want long 10000`
* get an alert when price falls short of 10000 - `/want short 10000`
* get price-movement notifiers based on currently held position - `/position long 10000 sl 9800`
  - will alert on every 35 price change step (price flapping ommited);
  - will alert when target price reached - implicilty set to +70
  - will alert when stop loss price reached

Overall commands:
1. `/want {long|short} <price:int>`
2. `/position (long|short) <price:int> sl <stop loss price:int>`
3. `/jobs`
4. `/ end {want|position} - end jobs in your selected category")`

## Installation
`pip install python-telegram-bot requests`

credentials file format:
{
  "token": "XX"
}
