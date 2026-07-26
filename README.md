# Sure MCP Server

A Model Context Protocol (MCP) server for integrating with the [Sure](https://github.com/we-promise/sure) self-hosted personal finance platform. This server provides access to your financial accounts, transactions, investment trades and holdings, categories, and AI chat through Claude Desktop.

## Quick Start

### 1. Installation

1. **Clone this repository**:
   ```bash
   git clone https://github.com/robcerda/sure-mcp-server.git
   cd sure-mcp-server
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

3. **Configure Claude Desktop**:
   Add this to your Claude Desktop configuration file:

   **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

   **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

   ```json
   {
     "mcpServers": {
       "Sure": {
         "command": "uv",
         "args": [
           "run",
           "--with",
           "mcp[cli]",
           "--with-editable",
           "/path/to/your/sure-mcp-server",
           "mcp",
           "run",
           "/path/to/your/sure-mcp-server/src/sure_mcp_server/server.py"
         ],
         "env": {
           "SURE_API_URL": "http://localhost:3000",
           "SURE_API_KEY": "your-api-key-here"
         }
       }
     }
   }
   ```

   **Important**: Replace `/path/to/your/sure-mcp-server` with your actual path!

4. **Restart Claude Desktop**

### 2. Get Your Sure API Key

1. Start your Sure Docker instance: `docker compose up -d`
2. Log into Sure at `http://localhost:3000`
3. Go to **Settings > API Key** and generate a new key
4. Copy the API key to your Claude Desktop config

### 3. Start Using in Claude Desktop

Once configured, use these tools directly in Claude Desktop:
- `get_accounts` - View all accounts
- `get_transactions` - Recent transactions
- `get_categories` - Transaction categories
- `sync_accounts` - Trigger account sync

## Available Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `setup_authentication` | Get setup instructions | None |
| `check_auth_status` | Check authentication status | None |
| `check_connection` | Test API connection | None |
| `get_accounts` | Get all financial accounts | None |
| `get_transactions` | Get transactions with filtering | `limit`, `start_date`, `end_date`, `account_ids`, `category_ids`, `search` |
| `get_transaction` | Get single transaction | `transaction_id` |
| `create_transaction` | Create new transaction | `account_id`, `amount`, `name`, `date`, `category_id`, `notes`, `nature` |
| `update_transaction` | Update transaction | `transaction_id`, `amount`, `name`, `date`, `category_id`, `notes` |
| `delete_transaction` | Delete transaction | `transaction_id` |
| `get_trades` | Get investment trades with filtering | `limit`, `account_id`, `account_ids`, `start_date`, `end_date` |
| `get_trade` | Get single trade | `trade_id` |
| `create_trade` | Record a stock buy/sell/dividend/deposit/withdrawal/interest | `account_id`, `trade_type`, `date`, `ticker`, `security_id`, `manual_ticker`, `qty`, `price`, `amount`, `fee`, `currency`, `category_id`, `investment_activity_label`, `transfer_account_id` |
| `update_trade` | Update trade | `trade_id`, `trade_type`, `date`, `qty`, `price`, `amount`, `currency`, `category_id`, `investment_activity_label`, `notes` |
| `delete_trade` | Delete trade | `trade_id` |
| `get_holdings` | Get stock holdings (read-only) with filtering | `limit`, `account_id`, `account_ids`, `security_id`, `date`, `start_date`, `end_date` |
| `get_holding` | Get single holding | `holding_id` |
| `get_categories` | Get all categories | None |
| `get_category` | Get single category | `category_id` |
| `sync_accounts` | Trigger account sync | None |
| `get_usage` | Get API usage info | None |
| `list_chats` | List AI chat sessions | None |
| `create_chat` | Create new chat | `title` |
| `get_chat` | Get chat details | `chat_id` |
| `send_message` | Send message to AI | `chat_id`, `content` |
| `delete_chat` | Delete chat session | `chat_id` |

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SURE_API_URL` | Yes | - | Base URL of your Sure instance |
| `SURE_API_KEY` | Yes | - | API key from Sure settings |
| `SURE_TIMEOUT` | No | 30 | Request timeout in seconds |
| `SURE_VERIFY_SSL` | No | true | Verify SSL certificates |

For local Docker setup, use `SURE_API_URL=http://localhost:3000` and `SURE_VERIFY_SSL=false`.

## Date Formats

- All dates should be in `YYYY-MM-DD` format (e.g., "2024-12-15")
- Transaction amounts: use `nature` field to specify "income" or "expense"

## Investment Trades

`create_trade` requires the target account to be an **investment** account
(or a crypto account with subtype "exchange") -- Sure rejects trades on
regular bank/card accounts. Required fields depend on `trade_type`:

| `trade_type` | Required fields | Notes |
|---|---|---|
| `buy` / `sell` | `account_id`, `date`, `qty`, `price`, plus one of `ticker` / `security_id` / `manual_ticker` | `fee` and `currency` optional |
| `dividend` | `account_id`, `date`, `amount`, plus one of `ticker` / `security_id` / `manual_ticker` | |
| `interest` | `account_id`, `date`, `amount` | `ticker`/`manual_ticker` optional |
| `deposit` / `withdrawal` | `account_id`, `date`, `amount` | optional `transfer_account_id` links it to another account as a transfer |

`get_holdings` / `get_holding` are read-only -- Sure computes current stock
positions automatically from your trade history and market prices, so there
is no create/update/delete for holdings.

## Troubleshooting

### Connection Issues
1. Verify Sure is running: `docker compose ps`
2. Check the API URL is correct
3. Try `check_connection` tool to diagnose

### Authentication Issues
1. Verify your API key is correct
2. Check the key hasn't expired
3. Regenerate the key in Sure settings

## Project Structure

```
sure-mcp-server/
├── src/sure_mcp_server/
│   ├── __init__.py
│   └── server.py         # Main server implementation
├── pyproject.toml
├── requirements.txt
└── README.md
```

## License

MIT License
