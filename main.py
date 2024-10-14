#!/usr/bin/env python3

import asyncio
import os
from asyncstdlib import enumerate
from solana.rpc.async_api import AsyncClient
from solana.rpc.websocket_api import connect, RpcTransactionLogsFilterMentions
from solana.rpc.types import Commitment
from solders.pubkey import Pubkey
from solders.signature import Signature
import httpx
import random
from dotenv import load_dotenv
import websockets

load_dotenv()

HEARTBEAT_INTERVAL = 30  # Send a heartbeat every 30 seconds
HEARTBEAT_TIMEOUT = 10  # Wait 10 seconds for a heartbeat response

async def listen_with_retry():
    max_retries = 5
    base_delay = 1
    
    while True:
        try:
            await listen()
        except Exception as e:
            print(f"Connection error: {e}")
            for attempt in range(max_retries):
                delay = (2 ** attempt + random.uniform(0, 1)) * base_delay
                print(f"Reconnecting in {delay:.2f} seconds...")
                await asyncio.sleep(delay)
                try:
                    await listen()
                    break  # If successful, break out of the retry loop
                except Exception as e:
                    print(f"Reconnection attempt {attempt + 1} failed: {e}")
            else:
                print("Max retries reached. Restarting from the beginning.")

async def heartbeat(websocket):
    while True:
        try:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            await websocket.ping()
            await asyncio.wait_for(websocket.pong(), timeout=HEARTBEAT_TIMEOUT)
        except asyncio.TimeoutError:
            print("Heartbeat timeout")
            raise websockets.exceptions.ConnectionClosed(1000, "Heartbeat timeout")
        except websockets.exceptions.ConnectionClosed:
            raise

async def listen():
    rpcFilter = RpcTransactionLogsFilterMentions(
        pubkey=Pubkey.from_string(os.getenv("PUBKEY"))
    )
    solana_client = AsyncClient(os.getenv("SOLANA_RPC_HTTP_URL"))
    
    async with connect(os.getenv("SOLANA_RPC_WS_URL")) as websocket:
        try:
            heartbeat_task = asyncio.create_task(heartbeat(websocket))
            
            await websocket.logs_subscribe(rpcFilter, Commitment("confirmed"))
            first_resp = await websocket.recv()
            subscription_id = first_resp[0].result
            
            async for idx, msg in enumerate(websocket):
                try:
                    s = str(msg[0].result.value.signature)
                    sig = Signature.from_string(s)
                    tx = await solana_client.get_transaction(sig, "json", Commitment("confirmed"), max_supported_transaction_version=0)
                    j = tx.to_json()
                    async with httpx.AsyncClient() as client:
                        await client.post(os.getenv("WEBHOOK_URL"), data=j, headers={"Content-Type": "application/json"})
                except Exception as e:
                    print(f"Error processing transaction: {e}")
        except websockets.exceptions.ConnectionClosed:
            print("WebSocket connection closed. Attempting to reconnect...")
            raise
        finally:
            heartbeat_task.cancel()
            try:
                await websocket.logs_unsubscribe(subscription_id)
            except Exception:
                pass

def main():
    asyncio.run(listen_with_retry())

if __name__ == "__main__":
    main()
