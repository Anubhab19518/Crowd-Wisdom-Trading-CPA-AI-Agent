"""Prompt templates for OpenRouter LLM usage.

Provides prompt-building helpers for classification and extraction tasks.
"""
from typing import Optional


def classify_prompt(text: str, filename: Optional[str] = None) -> str:
    # Few-shot examples to improve classification reliability
    examples = (
        "Example 1:\nText: Invoice for shipment charges, total due $1,234.\nLabel: invoice\n\n"
        "Example 2:\nText: Bill of lading - container details, consignee, vessel and voyage.\nLabel: bill_of_lading\n\n"
        "Example 3:\nText: Packing list: 20 boxes, item descriptions, weights.\nLabel: packing_list\n\n"
    )
    return (
        "You are an assistant that classifies shipping/logistics documents. "
        "Return exactly one word label and nothing else: one of: invoice, bill_of_lading, packing_list, other.\n\n"
        f"{examples}Filename: {filename or ''}\nDocument text:\n" + (text or '') + "\n\nLabel:"
    )


def extract_json_prompt(text: str, filename: Optional[str] = None, metadata: dict = None) -> str:
    md = metadata or {}
    examples = (
        "Example 1:\nText: Invoice from ABC Co. Total: $1,234.56.\nJSON:{\"vendor\":\"ABC Co\",\"amount\":1234.56,\"currency\":\"USD\",\"route\":null,\"date\":null}\n\n"
        "Example 2:\nText: Bill of lading: Shipper: XYZ, Amount: 2,345 USD, Route: Shanghai -> LA, Date: 2025-01-20.\nJSON:{\"vendor\":\"XYZ\",\"amount\":2345,\"currency\":\"USD\",\"route\":\"Shanghai -> LA\",\"date\":\"2025-01-20\"}\n\n"
    )
    return (
        "Extract the following JSON object with keys: vendor, amount, currency, route, date. "
        "If a value is missing, set it to null. Amount should be a number (no currency symbol). "
        "Return only the JSON object and nothing else. Use the examples as guidance.\n\n"
        f"{examples}Filename: {filename or ''}\nMetadata: {md}\nDocument text:\n" + (text or '') + "\n\nJSON:"
    )
