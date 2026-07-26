"""Sure MCP Server - Main server implementation."""

import os
import logging
import json
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("Sure MCP Server")


def get_api_url() -> str:
    """Get the Sure API base URL."""
    url = os.getenv("SURE_API_URL")
    if not url:
        raise RuntimeError("❌ SURE_API_URL not configured. Set it in your environment.")
    return url.rstrip("/")


def get_auth_header() -> Dict[str, str]:
    """Get authentication header for API requests."""
    api_key = os.getenv("SURE_API_KEY")
    access_token = os.getenv("SURE_ACCESS_TOKEN")

    if api_key:
        return {"X-Api-Key": api_key}
    elif access_token:
        return {"Authorization": f"Bearer {access_token}"}
    else:
        raise RuntimeError("❌ No authentication configured. Set SURE_API_KEY or SURE_ACCESS_TOKEN.")


def get_client() -> httpx.Client:
    """Get configured HTTP client for Sure API."""
    timeout = int(os.getenv("SURE_TIMEOUT", "30"))
    verify_ssl = os.getenv("SURE_VERIFY_SSL", "true").lower() == "true"

    return httpx.Client(
        base_url=get_api_url(),
        timeout=timeout,
        verify=verify_ssl,
        headers=get_auth_header()
    )


def handle_response(response: httpx.Response) -> Any:
    """Handle API response and raise appropriate errors."""
    if response.status_code == 401:
        raise RuntimeError("❌ Authentication failed. Check your API key.")
    elif response.status_code == 403:
        raise RuntimeError("❌ Permission denied. Check API key scopes.")
    elif response.status_code == 404:
        raise RuntimeError("❌ Resource not found.")
    elif response.status_code == 429:
        raise RuntimeError("❌ Rate limited. Please wait and try again.")
    elif response.status_code >= 400:
        raise RuntimeError(f"❌ API error {response.status_code}: {response.text}")

    if response.headers.get("content-type", "").startswith("application/json"):
        return response.json()
    return response.text


@mcp.tool()
def setup_authentication() -> str:
    """Get instructions for setting up authentication with Sure."""
    return """🔐 Sure MCP Server - Setup Instructions

1️⃣ Start your Sure Docker instance:
   cd /path/to/sure
   docker compose up -d

2️⃣ Log into Sure at http://localhost:3000

3️⃣ Go to Settings > API Key and generate a new key

4️⃣ Add to your Claude Desktop config:
   "env": {
     "SURE_API_URL": "http://localhost:3000",
     "SURE_API_KEY": "your-api-key-here"
   }

5️⃣ Restart Claude Desktop

✅ Start using Sure tools:
   • get_accounts - View all accounts
   • get_transactions - Recent transactions
   • get_categories - Transaction categories
   • sync_accounts - Trigger account sync"""


@mcp.tool()
def check_auth_status() -> str:
    """Check if authentication is configured for Sure API."""
    try:
        api_url = os.getenv("SURE_API_URL")
        api_key = os.getenv("SURE_API_KEY")
        access_token = os.getenv("SURE_ACCESS_TOKEN")

        status = ""

        if api_url:
            status += f"✅ API URL: {api_url}\n"
        else:
            status += "❌ SURE_API_URL not configured\n"

        if api_key:
            status += "✅ API Key configured\n"
        elif access_token:
            status += "✅ Access Token configured\n"
        else:
            status += "❌ No authentication configured (SURE_API_KEY or SURE_ACCESS_TOKEN)\n"

        status += "\n💡 Try get_accounts to test the connection."

        return status
    except Exception as e:
        return f"Error checking auth status: {str(e)}"


@mcp.tool()
def check_connection() -> str:
    """Test connection to Sure API."""
    try:
        with get_client() as client:
            response = client.get("/api/v1/usage")
            data = handle_response(response)

            return f"✅ Connected to Sure API\n{json.dumps(data, indent=2, default=str)}"
    except Exception as e:
        logger.error(f"Failed to connect: {e}")
        return f"❌ Connection failed: {str(e)}"


@mcp.tool()
def get_accounts() -> str:
    """Get all financial accounts from Sure."""
    try:
        with get_client() as client:
            response = client.get("/api/v1/accounts")
            data = handle_response(response)

            # Handle paginated response
            accounts = data.get("accounts") or data.get("data") or data
            if isinstance(accounts, dict):
                accounts = accounts.get("accounts", [])

            logger.info(f"✅ Retrieved {len(accounts) if isinstance(accounts, list) else 'unknown'} accounts")
            return json.dumps(accounts, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to get accounts: {e}")
        return f"Error getting accounts: {str(e)}"


@mcp.tool()
def get_transactions(
    limit: int = 25,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    account_ids: Optional[str] = None,
    category_ids: Optional[str] = None,
    search: Optional[str] = None,
) -> str:
    """
    Get transactions from Sure.

    Args:
        limit: Number of transactions per page (default: 25, max: 100)
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        account_ids: Comma-separated account IDs to filter by
        category_ids: Comma-separated category IDs to filter by
        search: Search term to filter transactions
    """
    try:
        with get_client() as client:
            params: Dict[str, Any] = {"per_page": min(limit, 100)}

            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
            if account_ids:
                params["account_ids"] = account_ids
            if category_ids:
                params["category_ids"] = category_ids
            if search:
                params["search"] = search

            response = client.get("/api/v1/transactions", params=params)
            data = handle_response(response)

            # Handle paginated response
            transactions = data.get("transactions") or data.get("data") or data
            if isinstance(transactions, dict):
                transactions = transactions.get("transactions", [])

            logger.info(f"✅ Retrieved {len(transactions) if isinstance(transactions, list) else 'unknown'} transactions")
            return json.dumps(transactions, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to get transactions: {e}")
        return f"Error getting transactions: {str(e)}"


@mcp.tool()
def get_transaction(transaction_id: str) -> str:
    """
    Get a single transaction by ID.

    Args:
        transaction_id: The ID of the transaction
    """
    try:
        with get_client() as client:
            response = client.get(f"/api/v1/transactions/{transaction_id}")
            data = handle_response(response)

            return json.dumps(data, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to get transaction: {e}")
        return f"Error getting transaction: {str(e)}"


@mcp.tool()
def create_transaction(
    account_id: str,
    amount: float,
    name: str,
    date: str,
    category_id: Optional[str] = None,
    notes: Optional[str] = None,
    nature: Optional[str] = None,
) -> str:
    """
    Create a new transaction in Sure.

    Args:
        account_id: The account ID to add the transaction to
        amount: Transaction amount (use nature to specify income/expense)
        name: Transaction name/payee
        date: Transaction date in YYYY-MM-DD format
        category_id: Optional category ID
        notes: Optional notes
        nature: Optional "income" or "expense" to set amount sign
    """
    try:
        with get_client() as client:
            payload: Dict[str, Any] = {
                "account_id": account_id,
                "amount": amount,
                "name": name,
                "date": date,
            }

            if category_id:
                payload["category_id"] = category_id
            if notes:
                payload["notes"] = notes
            if nature:
                payload["nature"] = nature

            response = client.post(
                "/api/v1/transactions",
                json={"transaction": payload}
            )
            data = handle_response(response)

            logger.info(f"✅ Created transaction")
            return json.dumps(data, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to create transaction: {e}")
        return f"Error creating transaction: {str(e)}"


@mcp.tool()
def update_transaction(
    transaction_id: str,
    amount: Optional[float] = None,
    name: Optional[str] = None,
    date: Optional[str] = None,
    category_id: Optional[str] = None,
    notes: Optional[str] = None,
) -> str:
    """
    Update an existing transaction in Sure.

    Args:
        transaction_id: The ID of the transaction to update
        amount: New transaction amount
        name: New transaction name/payee
        date: New transaction date in YYYY-MM-DD format
        category_id: New category ID
        notes: New notes
    """
    try:
        with get_client() as client:
            payload: Dict[str, Any] = {}

            if amount is not None:
                payload["amount"] = amount
            if name is not None:
                payload["name"] = name
            if date is not None:
                payload["date"] = date
            if category_id is not None:
                payload["category_id"] = category_id
            if notes is not None:
                payload["notes"] = notes

            response = client.patch(
                f"/api/v1/transactions/{transaction_id}",
                json={"transaction": payload}
            )
            data = handle_response(response)

            logger.info(f"✅ Updated transaction {transaction_id}")
            return json.dumps(data, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to update transaction: {e}")
        return f"Error updating transaction: {str(e)}"


@mcp.tool()
def delete_transaction(transaction_id: str) -> str:
    """
    Delete a transaction from Sure.

    Args:
        transaction_id: The ID of the transaction to delete
    """
    try:
        with get_client() as client:
            response = client.delete(f"/api/v1/transactions/{transaction_id}")
            data = handle_response(response)

            logger.info(f"✅ Deleted transaction {transaction_id}")
            return json.dumps(data, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to delete transaction: {e}")
        return f"Error deleting transaction: {str(e)}"


@mcp.tool()
def get_trades(
    limit: int = 25,
    account_id: Optional[str] = None,
    account_ids: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> str:
    """
    Get investment trades (stock buys/sells/dividends/etc.) from Sure.

    Args:
        limit: Number of trades per page (default: 25, max: 100)
        account_id: Filter by a single investment account ID
        account_ids: Comma-separated account IDs to filter by
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    """
    try:
        with get_client() as client:
            params: Dict[str, Any] = {"per_page": min(limit, 100)}

            if account_id:
                params["account_id"] = account_id
            if account_ids:
                params["account_ids"] = account_ids
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date

            response = client.get("/api/v1/trades", params=params)
            data = handle_response(response)

            # Handle paginated response
            trades = data.get("trades") or data.get("data") or data
            if isinstance(trades, dict):
                trades = trades.get("trades", [])

            logger.info(f"✅ Retrieved {len(trades) if isinstance(trades, list) else 'unknown'} trades")
            return json.dumps(trades, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to get trades: {e}")
        return f"Error getting trades: {str(e)}"


@mcp.tool()
def get_trade(trade_id: str) -> str:
    """
    Get a single trade by ID.

    Args:
        trade_id: The ID of the trade
    """
    try:
        with get_client() as client:
            response = client.get(f"/api/v1/trades/{trade_id}")
            data = handle_response(response)

            return json.dumps(data, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to get trade: {e}")
        return f"Error getting trade: {str(e)}"


@mcp.tool()
def create_trade(
    account_id: str,
    trade_type: str,
    date: str,
    ticker: Optional[str] = None,
    security_id: Optional[str] = None,
    manual_ticker: Optional[str] = None,
    qty: Optional[float] = None,
    price: Optional[float] = None,
    amount: Optional[float] = None,
    fee: Optional[float] = None,
    currency: Optional[str] = None,
    category_id: Optional[str] = None,
    investment_activity_label: Optional[str] = None,
    transfer_account_id: Optional[str] = None,
) -> str:
    """
    Record a stock trade on an investment account in Sure (buy, sell,
    dividend, deposit, withdrawal, or interest). The account must be an
    investment account (or a crypto account of subtype "exchange") -- Sure
    rejects trades on regular bank/card accounts.

    Args:
        account_id: The investment account ID to record the trade against
        trade_type: One of "buy", "sell", "dividend", "deposit", "withdrawal", "interest"
        date: Trade date in YYYY-MM-DD format
        ticker: Stock ticker symbol (e.g. "AAPL", "RELIANCE") -- required for
                buy/sell/dividend unless security_id or manual_ticker is given
        security_id: Sure's internal security ID, as an alternative to ticker
        manual_ticker: Ticker for a security Sure doesn't track market prices for
        qty: Number of shares -- required for buy/sell
        price: Price per share -- required for buy/sell
        amount: Total cash amount -- required for dividend/deposit/withdrawal/interest
        fee: Optional broker fee, applies to buy/sell
        currency: Optional currency code, defaults to the account's currency
        category_id: Optional category ID
        investment_activity_label: Optional activity label (same list as transactions)
        transfer_account_id: Optional linked account for deposit/withdrawal transfers
    """
    try:
        with get_client() as client:
            payload: Dict[str, Any] = {
                "account_id": account_id,
                "type": trade_type,
                "date": date,
            }

            if ticker:
                payload["ticker"] = ticker
            if security_id:
                payload["security_id"] = security_id
            if manual_ticker:
                payload["manual_ticker"] = manual_ticker
            if qty is not None:
                payload["qty"] = qty
            if price is not None:
                payload["price"] = price
            if amount is not None:
                payload["amount"] = amount
            if fee is not None:
                payload["fee"] = fee
            if currency:
                payload["currency"] = currency
            if category_id:
                payload["category_id"] = category_id
            if investment_activity_label:
                payload["investment_activity_label"] = investment_activity_label
            if transfer_account_id:
                payload["transfer_account_id"] = transfer_account_id

            response = client.post(
                "/api/v1/trades",
                json={"trade": payload}
            )
            data = handle_response(response)

            logger.info("✅ Created trade")
            return json.dumps(data, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to create trade: {e}")
        return f"Error creating trade: {str(e)}"


@mcp.tool()
def update_trade(
    trade_id: str,
    trade_type: Optional[str] = None,
    date: Optional[str] = None,
    qty: Optional[float] = None,
    price: Optional[float] = None,
    amount: Optional[float] = None,
    currency: Optional[str] = None,
    category_id: Optional[str] = None,
    investment_activity_label: Optional[str] = None,
    notes: Optional[str] = None,
) -> str:
    """
    Update an existing trade in Sure.

    Args:
        trade_id: The ID of the trade to update
        trade_type: New type, one of "buy", "sell", "dividend", "deposit", "withdrawal", "interest"
        date: New trade date in YYYY-MM-DD format
        qty: New number of shares
        price: New price per share
        amount: New total cash amount
        currency: New currency code
        category_id: New category ID
        investment_activity_label: New activity label
        notes: New notes
    """
    try:
        with get_client() as client:
            payload: Dict[str, Any] = {}

            if trade_type is not None:
                payload["type"] = trade_type
            if date is not None:
                payload["date"] = date
            if qty is not None:
                payload["qty"] = qty
            if price is not None:
                payload["price"] = price
            if amount is not None:
                payload["amount"] = amount
            if currency is not None:
                payload["currency"] = currency
            if category_id is not None:
                payload["category_id"] = category_id
            if investment_activity_label is not None:
                payload["investment_activity_label"] = investment_activity_label
            if notes is not None:
                payload["notes"] = notes

            response = client.patch(
                f"/api/v1/trades/{trade_id}",
                json={"trade": payload}
            )
            data = handle_response(response)

            logger.info(f"✅ Updated trade {trade_id}")
            return json.dumps(data, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to update trade: {e}")
        return f"Error updating trade: {str(e)}"


@mcp.tool()
def delete_trade(trade_id: str) -> str:
    """
    Delete a trade from Sure.

    Args:
        trade_id: The ID of the trade to delete
    """
    try:
        with get_client() as client:
            response = client.delete(f"/api/v1/trades/{trade_id}")
            data = handle_response(response)

            logger.info(f"✅ Deleted trade {trade_id}")
            return json.dumps(data, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to delete trade: {e}")
        return f"Error deleting trade: {str(e)}"


@mcp.tool()
def get_holdings(
    limit: int = 25,
    account_id: Optional[str] = None,
    account_ids: Optional[str] = None,
    security_id: Optional[str] = None,
    date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> str:
    """
    Get stock holdings (positions) from Sure. Holdings are a read-only
    snapshot Sure computes automatically from trades and market prices --
    there is no create/update/delete for them, only viewing.

    Args:
        limit: Number of holdings per page (default: 25, max: 100)
        account_id: Filter by a single investment account ID
        account_ids: Comma-separated account IDs to filter by
        security_id: Filter by a single security ID
        date: Only return holdings as of this date (YYYY-MM-DD)
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    """
    try:
        with get_client() as client:
            params: Dict[str, Any] = {"per_page": min(limit, 100)}

            if account_id:
                params["account_id"] = account_id
            if account_ids:
                params["account_ids"] = account_ids
            if security_id:
                params["security_id"] = security_id
            if date:
                params["date"] = date
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date

            response = client.get("/api/v1/holdings", params=params)
            data = handle_response(response)

            # Handle paginated response
            holdings = data.get("holdings") or data.get("data") or data
            if isinstance(holdings, dict):
                holdings = holdings.get("holdings", [])

            logger.info(f"✅ Retrieved {len(holdings) if isinstance(holdings, list) else 'unknown'} holdings")
            return json.dumps(holdings, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to get holdings: {e}")
        return f"Error getting holdings: {str(e)}"


@mcp.tool()
def get_holding(holding_id: str) -> str:
    """
    Get a single holding by ID.

    Args:
        holding_id: The ID of the holding
    """
    try:
        with get_client() as client:
            response = client.get(f"/api/v1/holdings/{holding_id}")
            data = handle_response(response)

            return json.dumps(data, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to get holding: {e}")
        return f"Error getting holding: {str(e)}"


@mcp.tool()
def get_categories() -> str:
    """Get all transaction categories from Sure."""
    try:
        with get_client() as client:
            response = client.get("/api/v1/categories")
            data = handle_response(response)

            # Handle paginated response
            categories = data.get("categories") or data.get("data") or data
            if isinstance(categories, dict):
                categories = categories.get("categories", [])

            logger.info(f"✅ Retrieved {len(categories) if isinstance(categories, list) else 'unknown'} categories")
            return json.dumps(categories, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to get categories: {e}")
        return f"Error getting categories: {str(e)}"


@mcp.tool()
def get_category(category_id: str) -> str:
    """
    Get a single category by ID.

    Args:
        category_id: The ID of the category
    """
    try:
        with get_client() as client:
            response = client.get(f"/api/v1/categories/{category_id}")
            data = handle_response(response)

            return json.dumps(data, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to get category: {e}")
        return f"Error getting category: {str(e)}"


@mcp.tool()
def sync_accounts() -> str:
    """Trigger account sync to refresh data from financial institutions."""
    try:
        with get_client() as client:
            response = client.post("/api/v1/sync")
            data = handle_response(response)

            logger.info("✅ Triggered account sync")
            return json.dumps(data, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to sync accounts: {e}")
        return f"Error syncing accounts: {str(e)}"


@mcp.tool()
def get_usage() -> str:
    """Get API usage and rate limit information."""
    try:
        with get_client() as client:
            response = client.get("/api/v1/usage")
            data = handle_response(response)

            return json.dumps(data, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to get usage: {e}")
        return f"Error getting usage: {str(e)}"


@mcp.tool()
def list_chats() -> str:
    """Get all AI chat sessions from Sure."""
    try:
        with get_client() as client:
            response = client.get("/api/v1/chats")
            data = handle_response(response)

            # Handle paginated response
            chats = data.get("chats") or data.get("data") or data
            if isinstance(chats, dict):
                chats = chats.get("chats", [])

            logger.info(f"✅ Retrieved {len(chats) if isinstance(chats, list) else 'unknown'} chats")
            return json.dumps(chats, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to list chats: {e}")
        return f"Error listing chats: {str(e)}"


@mcp.tool()
def create_chat(title: Optional[str] = None) -> str:
    """
    Create a new AI chat session in Sure.

    Args:
        title: Optional title for the chat
    """
    try:
        with get_client() as client:
            payload: Dict[str, Any] = {}
            if title:
                payload["title"] = title

            response = client.post("/api/v1/chats", json=payload)
            data = handle_response(response)

            logger.info("✅ Created new chat")
            return json.dumps(data, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to create chat: {e}")
        return f"Error creating chat: {str(e)}"


@mcp.tool()
def get_chat(chat_id: str) -> str:
    """
    Get a chat session by ID.

    Args:
        chat_id: The ID of the chat
    """
    try:
        with get_client() as client:
            response = client.get(f"/api/v1/chats/{chat_id}")
            data = handle_response(response)

            return json.dumps(data, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to get chat: {e}")
        return f"Error getting chat: {str(e)}"


@mcp.tool()
def send_message(chat_id: str, content: str) -> str:
    """
    Send a message to Sure's AI assistant.

    Args:
        chat_id: The ID of the chat
        content: The message content
    """
    try:
        with get_client() as client:
            response = client.post(
                f"/api/v1/chats/{chat_id}/messages",
                json={"content": content}
            )
            data = handle_response(response)

            logger.info("✅ Sent message")
            return json.dumps(data, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        return f"Error sending message: {str(e)}"


@mcp.tool()
def delete_chat(chat_id: str) -> str:
    """
    Delete a chat session.

    Args:
        chat_id: The ID of the chat to delete
    """
    try:
        with get_client() as client:
            response = client.delete(f"/api/v1/chats/{chat_id}")
            data = handle_response(response)

            logger.info(f"✅ Deleted chat {chat_id}")
            return json.dumps(data, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to delete chat: {e}")
        return f"Error deleting chat: {str(e)}"


def main():
    """Main entry point for the server."""
    logger.info("Starting Sure MCP Server...")
    try:
        mcp.run()
    except Exception as e:
        logger.error(f"Failed to run server: {str(e)}")
        raise


# Export for mcp run
app = mcp

if __name__ == "__main__":
    main()
