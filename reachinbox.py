#!/usr/bin/env python3
"""
ReachInbox CLI — full programmatic access to ReachInbox via the self-hosted proxy.
All commands proxy through REACHINBOX_PROXY_URL (default: https://reachinbox.luxeillum.com).
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from urllib.parse import urlencode

PROXY_URL = os.environ.get("REACHINBOX_PROXY_URL", "http://172.30.0.3:3000")

# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _req(method, path, body=None):
    url = f"{PROXY_URL}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read())
        except Exception:
            return {"error": f"HTTP {e.code}", "message": str(e)}

def _get(path, **params):
    params = {k: v for k, v in params.items() if v is not None}
    qs = f"?{urlencode(params)}" if params else ""
    return _req("GET", f"{path}{qs}")

def _post(path, body=None):
    return _req("POST", path, body or {})

def _delete(path):
    return _req("DELETE", path)

def _qs(**kwargs):
    return {k: v for k, v in kwargs.items() if v is not None}

# ── Output ────────────────────────────────────────────────────────────────────

def _out(data):
    print(json.dumps(data, indent=2, default=str))

# ══════════════════════════════════════════════════════════════════════════════
# Campaigns
# ══════════════════════════════════════════════════════════════════════════════

def cmd_campaign_list(args):
    _out(_get("/api/v1/campaign/list", **_qs(limit=args.limit, filter=args.filter, sort=args.sort)))

def cmd_campaign_create(args):
    _out(_post("/api/v1/campaign/create", {"name": args.name}))

def cmd_campaign_start(args):
    _out(_post("/api/v1/campaign/start", {"campaignId": args.campaign_id}))

def cmd_campaign_pause(args):
    _out(_post("/api/v1/campaign/pause", {"campaignId": args.campaign_id}))

def cmd_campaign_update(args):
    body = {"campaignId": args.campaign_id}
    for k in ("name", "scheduleType", "timezone"):
        v = getattr(args, k, None)
        if v is not None:
            body[k] = v
    _out(_post("/api/v1/campaign/update", body))

def cmd_campaign_analytics(args):
    _out(_post("/api/v1/campaign/analytics", {"campaignId": args.campaign_id}))

def cmd_campaign_total_analytics(args):
    _out(_post("/api/v1/campaign/total-analytics", _qs(startDate=args.start_date, endDate=args.end_date)))

def cmd_campaign_details(args):
    _out(_get("/api/v1/campaign/details", campaignId=args.campaign_id))

def cmd_campaign_options(args):
    _out(_get("/api/v1/campaign/options", campaignId=args.campaign_id))

def cmd_campaign_schedule(args):
    _out(_get("/api/v1/campaign/schedule", campaignId=args.campaign_id))

def cmd_campaign_accounts(args):
    _out(_get("/api/v1/campaign/list-accounts", campaignId=args.campaign_id, limit=args.limit))

def cmd_campaign_account_errors(args):
    _out(_get("/api/v1/campaign/list-accounts-errors", campaignId=args.campaign_id, limit=args.limit))

def cmd_campaign_delete(args):
    _out(_delete(f"/api/v1/campaign/delete?campaignId={args.campaign_id}"))

def cmd_campaign_save_options(args):
    _out(_post("/api/v1/campaign/update-options", {"campaignId": str(args.campaign_id), **args.payload}))

def cmd_campaign_save_schedule(args):
    _out(_post("/api/v1/schedule/add", {"campaignId": str(args.campaign_id), **args.payload}))

def cmd_campaign_sequences_get(args):
    _out(_get("/api/v1/campaign/sequences", campaignId=args.campaign_id))

def cmd_campaign_sequences_save(args):
    body = {"campaignId": args.campaign_id, "sequences": args.sequences}
    if args.core_variables is not None:
        body["coreVariables"] = args.core_variables
    _out(_post("/api/v1/sequences/add", body))

def cmd_campaign_get_bundle(args):
    """Fetch a full settings bundle (details + options + schedule + sequences + subsequences)."""
    cid = args.campaign_id
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    def fetch(path):
        return _get(path, campaignId=cid)

    def fetch_subseq(sid):
        return _get(f"/api/v1/subsequence/details", subsequenceId=sid)

    details = fetch("/api/v1/campaign/details")
    options = fetch("/api/v1/campaign/options")
    schedule = fetch("/api/v1/campaign/schedule")
    sequences = fetch("/api/v1/campaign/sequences")
    subseq_list = fetch("/api/v1/subsequence/list")

    subseq_rows = subseq_list.get("data") or subseq_list
    if isinstance(subseq_rows, dict):
        subseq_rows = subseq_rows.get("subsequences") or subseq_rows.get("rows") or []

    subseq_details = []
    for row in subseq_rows:
        sid = row.get("subsequenceId") or row.get("id") or row.get("subSequenceId")
        if sid:
            subseq_details.append(fetch_subseq(sid))

    _out({
        "campaignId": cid,
        "details": details.get("data", details),
        "options": options.get("data", options),
        "schedule": schedule.get("data", schedule),
        "sequences": sequences.get("data", sequences),
        "subsequences": subseq_details,
    })

def cmd_campaign_apply_bundle(args):
    """Apply a settings bundle to a campaign (reads bundle from file)."""
    with open(args.bundle_file) as f:
        bundle = json.load(f)
    behavior = _qs(
        includeName=args.include_name,
        includeOptions=args.include_options,
        includeSchedule=args.include_schedule,
        includeSequences=args.include_sequences,
        includeSubsequences=args.include_subsequences,
    )
    _out(_post("/api/v1/campaign/apply-bundle", {
        "campaignId": args.campaign_id,
        "bundle": bundle,
        "behavior": behavior,
    }))

def cmd_campaign_copy_settings(args):
    """Copy settings from one campaign to another."""
    behavior = _qs(
        includeName=args.include_name,
        includeOptions=args.include_options,
        includeSchedule=args.include_schedule,
        includeSequences=args.include_sequences,
        includeSubsequences=args.include_subsequences,
    )
    _out(_post("/api/v1/campaign/copy-settings", {
        "sourceCampaignId": args.source_campaign_id,
        "targetCampaignId": args.target_campaign_id,
        "behavior": behavior,
    }))

# ══════════════════════════════════════════════════════════════════════════════
# Schedule templates
# ══════════════════════════════════════════════════════════════════════════════

def cmd_schedule_template_list(args):
    _out(_get("/api/v1/schedule/templates"))

def cmd_schedule_template_create(args):
    _out(_post("/api/v1/schedule/save-template", args.payload))

def cmd_schedule_template_update(args):
    _out(_req("PUT", f"/api/v1/schedule/template/{args.template_id}", args.payload))

def cmd_schedule_template_delete(args):
    _out(_delete(f"/api/v1/schedule/template/{args.template_id}"))

# ══════════════════════════════════════════════════════════════════════════════
# Subsequences
# ══════════════════════════════════════════════════════════════════════════════

def cmd_subsequence_list(args):
    _out(_get("/api/v1/subsequence/list", campaignId=args.campaign_id))

def cmd_subsequence_details(args):
    _out(_get("/api/v1/subsequence/details", subsequenceId=args.subsequence_id))

def cmd_subsequence_create(args):
    body = {"campaignId": args.campaign_id, "name": args.name}
    for k in ("subject", "body", "leadStatusCondition", "leadActivityCondition", "leadReplyText", "leadReplyContext"):
        v = getattr(args, k, None)
        if v is not None:
            body[k] = v
    _out(_post("/api/v1/subsequence/create", body))

def cmd_subsequence_update(args):
    body = {"subsequenceId": args.subsequence_id}
    for k in ("name", "subject", "body", "leadStatusCondition", "leadActivityCondition", "leadReplyText", "leadReplyContext"):
        v = getattr(args, k, None)
        if v is not None:
            body[k] = v
    _out(_post("/api/v1/subsequence/update", body))

# ══════════════════════════════════════════════════════════════════════════════
# Leads
# ══════════════════════════════════════════════════════════════════════════════

def cmd_leads_add(args):
    _out(_post("/api/v1/leads/add", {
        "campaignId": args.campaign_id,
        "leads": args.leads,
        "duplicates": args.duplicates or "skip",
    }))

def cmd_leads_update(args):
    body = {"campaignId": args.campaign_id, "email": args.email}
    for k in ("firstName", "lastName", "phone", "company", "title"):
        v = getattr(args, k, None)
        if v is not None:
            body[k] = v
    _out(_post("/api/v1/leads/update", body))

def cmd_leads_delete(args):
    _out(_post("/api/v1/leads/delete", {"campaignId": args.campaign_id, "emails": args.emails}))

# ══════════════════════════════════════════════════════════════════════════════
# Lead lists
# ══════════════════════════════════════════════════════════════════════════════

def cmd_lead_list_list(args):
    _out(_get("/api/v1/leads-list/all", limit=args.limit, contains=args.search))

def cmd_lead_list_create(args):
    _out(_post("/api/v1/leads-list/create", {"name": args.name}))

def cmd_lead_list_add_leads(args):
    _out(_post("/api/v1/leads-list/add-leads", {
        "leadsListId": args.list_id,
        "leads": args.leads,
        "newCoreVariables": args.core_variables or [],
        "duplicates": [],
    }))

def cmd_lead_list_get_leads(args):
    _out(_get("/api/v1/leads-list/all-leads",
        leadsListId=args.list_id,
        limit=args.limit,
        offset=args.offset,
        lastLead=str(args.last_lead).lower(),
    ))

def cmd_lead_list_update(args):
    _out(_req("PUT", "/api/v1/leads-list/update", {
        "leadsListId": args.list_id,
        "name": args.name,
    }))

def cmd_lead_list_add_to_campaign(args):
    _out(_post("/api/v1/lead-list/copy-leads-to-campaign", {
        "campaignId": args.campaign_id,
        "leadsListId": args.list_id,
    }))

def cmd_lead_list_delete(args):
    _out(_delete(f"/api/v1/leads-list/delete?leadsListId={args.list_id}"))

# ══════════════════════════════════════════════════════════════════════════════
# Accounts
# ══════════════════════════════════════════════════════════════════════════════

def cmd_account_list(args):
    _out(_get("/api/v1/account/list"))

def cmd_account_warmup(args):
    _out(_get("/api/v1/account/warmup-analytics"))

# ══════════════════════════════════════════════════════════════════════════════
# Onebox (Inbox)
# ══════════════════════════════════════════════════════════════════════════════

def cmd_inbox_list(args):
    _out(_post("/api/v1/onebox/list", {"page": args.page, "limit": args.limit}))

def cmd_inbox_send(args):
    body = {"threadId": args.thread_id, "body": args.body}
    if args.subject:
        body["subject"] = args.subject
    _out(_post("/api/v1/onebox/send", body))

def cmd_inbox_mark_read(args):
    _out(_post("/api/v1/onebox/mark-all-read", {}))

def cmd_inbox_unread(args):
    _out(_post("/api/v1/onebox/unread-count", {}))

def cmd_inbox_search(args):
    _out(_post("/api/v1/onebox/liveInbox/unifiedSearch", {"query": args.query, "page": args.page}))

# ══════════════════════════════════════════════════════════════════════════════
# Tags
# ══════════════════════════════════════════════════════════════════════════════

def cmd_tag_list(args):
    _out(_get("/api/v1/others/listAllTags"))

# ══════════════════════════════════════════════════════════════════════════════
# Webhooks
# ══════════════════════════════════════════════════════════════════════════════

def cmd_webhook_list(args):
    _out(_get("/api/v1/webhook/list-all"))

def cmd_webhook_subscribe(args):
    _out(_post("/api/v1/webhook/subscribe", {
        "campaignId": args.campaign_id,
        "event": args.event,
        "callbackUrl": args.callback_url,
        "allCampaigns": args.all_campaigns or False,
    }))

def cmd_webhook_unsubscribe(args):
    if args.id:
        _out(_delete(f"/api/v1/webhook/delete/{args.id}"))
    else:
        _out(_post("/api/v1/webhook/unsubscribe", {
            "campaignId": args.campaign_id,
            "event": args.event,
            "callbackUrl": args.callback_url,
        }))

# ══════════════════════════════════════════════════════════════════════════════
# Blocklist
# ══════════════════════════════════════════════════════════════════════════════

def cmd_blocklist_add(args):
    _out(_post("/api/v1/blocklist/add", {
        "emails": args.emails or [],
        "domains": args.domains or [],
        "keywords": args.keywords or [],
        "repliesKeywords": args.replies_keywords or [],
    }))

def cmd_blocklist_get(args):
    path = f"/api/v1/blocklist/{args.table}" if args.table else "/api/v1/blocklist"
    _out(_get(path, **_qs(limit=args.limit, offset=args.offset, q=args.q)))

def cmd_blocklist_delete(args):
    _out(_delete(f"/api/v1/blocklist/{args.table}", {"ids": args.ids}))

# ══════════════════════════════════════════════════════════════════════════════
# Health
# ══════════════════════════════════════════════════════════════════════════════

def cmd_health(args):
    _out(_get("/health"))

# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════

def build_parser():
    p = argparse.ArgumentParser(prog="reachinbox", description="ReachInbox CLI client")
    sub = p.add_subparsers(dest="command", required=True)

    # Health
    sp = sub.add_parser("health", help="Check proxy health")

    # Campaigns
    sp = sub.add_parser("campaigns", help="Campaign operations")
    csp = sp.add_subparsers(dest="action", required=True)

    cp = csp.add_parser("list", help="List campaigns")
    cp.add_argument("--limit", type=int, default=50)
    cp.add_argument("--filter", default="all", choices=["all", "active", "paused", "completed"])
    cp.add_argument("--sort", default="newest", choices=["newest", "oldest"])

    cp = csp.add_parser("create", help="Create campaign")
    cp.add_argument("name")

    cp = csp.add_parser("start", help="Start campaign")
    cp.add_argument("--campaign-id", type=int, required=True)

    cp = csp.add_parser("pause", help="Pause campaign")
    cp.add_argument("--campaign-id", type=int, required=True)

    cp = csp.add_parser("update", help="Update campaign")
    cp.add_argument("--campaign-id", type=int, required=True)
    cp.add_argument("--name")
    cp.add_argument("--schedule-type")
    cp.add_argument("--timezone")

    cp = csp.add_parser("analytics", help="Get campaign analytics")
    cp.add_argument("--campaign-id", type=int, required=True)

    cp = csp.add_parser("total-analytics", help="Total analytics")
    cp.add_argument("--start-date")
    cp.add_argument("--end-date")

    cp = csp.add_parser("details", help="Get campaign details")
    cp.add_argument("--campaign-id", type=int, required=True)

    cp = csp.add_parser("options", help="Get campaign options")
    cp.add_argument("--campaign-id", type=int, required=True)

    cp = csp.add_parser("schedule", help="Get campaign schedule")
    cp.add_argument("--campaign-id", type=int, required=True)

    cp = csp.add_parser("accounts", help="List campaign accounts")
    cp.add_argument("--campaign-id", type=int, required=True)
    cp.add_argument("--limit", type=int, default=5)

    cp = csp.add_parser("account-errors", help="List campaign account errors")
    cp.add_argument("--campaign-id", type=int, required=True)
    cp.add_argument("--limit", type=int, default=5)

    cp = csp.add_parser("delete", help="Delete campaign")
    cp.add_argument("--campaign-id", type=int, required=True)

    cp = csp.add_parser("save-options", help="Update campaign options")
    cp.add_argument("--campaign-id", type=int, required=True)
    cp.add_argument("--payload", type=json.loads, required=True, help="JSON options payload")

    cp = csp.add_parser("save-schedule", help="Replace campaign schedule")
    cp.add_argument("--campaign-id", type=int, required=True)
    cp.add_argument("--payload", type=json.loads, required=True, help="JSON schedule payload")

    cp = csp.add_parser("sequences-get", help="Get sequence builder payload")
    cp.add_argument("--campaign-id", type=int, required=True)

    cp = csp.add_parser("sequences-save", help="Save sequence builder steps")
    cp.add_argument("--campaign-id", type=int, required=True)
    cp.add_argument("--sequences", type=json.loads, required=True)
    cp.add_argument("--core-variables", type=json.loads)

    cp = csp.add_parser("get-bundle", help="Get full settings bundle")
    cp.add_argument("--campaign-id", type=int, required=True)

    cp = csp.add_parser("apply-bundle", help="Apply settings bundle from file")
    cp.add_argument("--campaign-id", type=int, required=True)
    cp.add_argument("--bundle-file", required=True)
    for flag in ("include-name", "include-options", "include-schedule", "include-sequences", "include-subsequences"):
        cp.add_argument(f"--{flag}", action=argparse.BooleanOptionalAction, default=None)

    cp = csp.add_parser("copy-settings", help="Copy settings between campaigns")
    cp.add_argument("--source-campaign-id", type=int, required=True)
    cp.add_argument("--target-campaign-id", type=int, required=True)
    for flag in ("include-name", "include-options", "include-schedule", "include-sequences", "include-subsequences"):
        cp.add_argument(f"--{flag}", action=argparse.BooleanOptionalAction, default=None)

    # Schedule templates
    sp = sub.add_parser("schedule-templates", help="Schedule template operations")
    tsp = sp.add_subparsers(dest="action", required=True)
    tsp.add_parser("list")
    cp = tsp.add_parser("create", help="Create schedule template")
    cp.add_argument("--payload", type=json.loads, required=True)
    cp = tsp.add_parser("update", help="Update schedule template")
    cp.add_argument("--template-id", type=int, required=True)
    cp.add_argument("--payload", type=json.loads, required=True)
    cp = tsp.add_parser("delete", help="Delete schedule template")
    cp.add_argument("--template-id", type=int, required=True)

    # Subsequences
    sp = sub.add_parser("subsequences", help="Subsequence operations")
    ssp = sp.add_subparsers(dest="action", required=True)
    cp = ssp.add_parser("list", help="List subsequences")
    cp.add_argument("--campaign-id", type=int, required=True)
    cp = ssp.add_parser("details", help="Get subsequence details")
    cp.add_argument("--subsequence-id", type=int, required=True)
    cp = ssp.add_parser("create", help="Create subsequence")
    cp.add_argument("--campaign-id", type=int, required=True)
    cp.add_argument("--name", required=True)
    for k in ("subject", "body", "leadStatusCondition", "leadActivityCondition", "leadReplyText", "leadReplyContext"):
        cp.add_argument(f"--{k}")
    cp = ssp.add_parser("update", help="Update subsequence")
    cp.add_argument("--subsequence-id", type=int, required=True)
    for k in ("name", "subject", "body", "leadStatusCondition", "leadActivityCondition", "leadReplyText", "leadReplyContext"):
        cp.add_argument(f"--{k}")

    # Leads
    sp = sub.add_parser("leads", help="Lead operations")
    lsp = sp.add_subparsers(dest="action", required=True)
    cp = lsp.add_parser("add", help="Add leads to campaign")
    cp.add_argument("--campaign-id", type=int, required=True)
    cp.add_argument("--leads", type=json.loads, required=True)
    cp.add_argument("--duplicates", default="skip")
    cp = lsp.add_parser("update", help="Update lead")
    cp.add_argument("--campaign-id", type=int, required=True)
    cp.add_argument("--email", required=True)
    for k in ("firstName", "lastName", "phone", "company", "title"):
        cp.add_argument(f"--{k}")
    cp = lsp.add_parser("delete", help="Delete leads from campaign")
    cp.add_argument("--campaign-id", type=int, required=True)
    cp.add_argument("--emails", type=json.loads, required=True)

    # Lead lists
    sp = sub.add_parser("lead-lists", help="Lead list operations")
    llsp = sp.add_subparsers(dest="action", required=True)
    cp = llsp.add_parser("list", help="List lead lists")
    cp.add_argument("--limit", type=int, default=50)
    cp.add_argument("--search")
    cp = llsp.add_parser("create", help="Create lead list")
    cp.add_argument("--name", required=True)
    cp = llsp.add_parser("add-leads", help="Add leads to list")
    cp.add_argument("--list-id", type=int, required=True)
    cp.add_argument("--leads", type=json.loads, required=True)
    cp.add_argument("--core-variables", type=json.loads)
    cp = llsp.add_parser("get-leads", help="Get leads from list")
    cp.add_argument("--list-id", type=int, required=True)
    cp.add_argument("--limit", type=int, default=50)
    cp.add_argument("--offset", type=int, default=0)
    cp.add_argument("--last-lead", action="store_true")
    cp = llsp.add_parser("update", help="Rename lead list")
    cp.add_argument("--list-id", type=int, required=True)
    cp.add_argument("--name", required=True)
    cp = llsp.add_parser("add-to-campaign", help="Add list leads to campaign")
    cp.add_argument("--list-id", type=int, required=True)
    cp.add_argument("--campaign-id", type=int, required=True)
    cp = llsp.add_parser("delete", help="Delete lead list")
    cp.add_argument("--list-id", type=int, required=True)

    # Accounts
    sp = sub.add_parser("accounts", help="Account operations")
    asp = sp.add_subparsers(dest="action", required=True)
    asp.add_parser("list", help="List connected email accounts")
    asp.add_parser("warmup", help="Get warmup analytics")

    # Inbox
    sp = sub.add_parser("inbox", help="Inbox (Onebox) operations")
    isp = sp.add_subparsers(dest="action", required=True)
    cp = isp.add_parser("list", help="List inbox threads")
    cp.add_argument("--page", type=int, default=1)
    cp.add_argument("--limit", type=int, default=20)
    cp = isp.add_parser("send", help="Send reply")
    cp.add_argument("--thread-id", required=True)
    cp.add_argument("--body", required=True)
    cp.add_argument("--subject")
    isp.add_parser("mark-read", help="Mark all as read")
    isp.add_parser("unread-count", help="Get unread count")
    cp = isp.add_parser("search", help="Search inbox")
    cp.add_argument("--query", required=True)
    cp.add_argument("--page", type=int, default=1)

    # Tags
    sub.add_parser("tags", help="List all tags")

    # Webhooks
    sp = sub.add_parser("webhooks", help="Webhook operations")
    wsp = sp.add_subparsers(dest="action", required=True)
    wsp.add_parser("list")
    cp = wsp.add_parser("subscribe")
    cp.add_argument("--campaign-id", type=int, required=True)
    cp.add_argument("--event", required=True)
    cp.add_argument("--callback-url", required=True)
    cp.add_argument("--all-campaigns", action="store_true")
    cp = wsp.add_parser("unsubscribe")
    cp.add_argument("--id")
    cp.add_argument("--campaign-id", type=int)
    cp.add_argument("--event")
    cp.add_argument("--callback-url")

    # Blocklist
    sp = sub.add_parser("blocklist", help="Blocklist operations")
    bsp = sp.add_subparsers(dest="action", required=True)
    cp = bsp.add_parser("add")
    cp.add_argument("--emails", type=json.loads, default=[])
    cp.add_argument("--domains", type=json.loads, default=[])
    cp.add_argument("--keywords", type=json.loads, default=[])
    cp.add_argument("--replies-keywords", type=json.loads, default=[])
    cp = bsp.add_parser("get")
    cp.add_argument("--table", choices=["emails", "domains", "keywords", "repliesKeywords"])
    cp.add_argument("--limit", type=int)
    cp.add_argument("--offset", type=int)
    cp.add_argument("--q")
    cp = bsp.add_parser("delete")
    cp.add_argument("--table", required=True, choices=["emails", "domains", "keywords", "repliesKeywords"])
    cp.add_argument("--ids", type=json.loads, required=True)

    return p

def main():
    p = build_parser()
    args = p.parse_args()

    dispatch = {
        "health": cmd_health,

        "campaigns": {
            "list": cmd_campaign_list,
            "create": cmd_campaign_create,
            "start": cmd_campaign_start,
            "pause": cmd_campaign_pause,
            "update": cmd_campaign_update,
            "analytics": cmd_campaign_analytics,
            "total-analytics": cmd_campaign_total_analytics,
            "details": cmd_campaign_details,
            "options": cmd_campaign_options,
            "schedule": cmd_campaign_schedule,
            "accounts": cmd_campaign_accounts,
            "account-errors": cmd_campaign_account_errors,
            "delete": cmd_campaign_delete,
            "save-options": cmd_campaign_save_options,
            "save-schedule": cmd_campaign_save_schedule,
            "sequences-get": cmd_campaign_sequences_get,
            "sequences-save": cmd_campaign_sequences_save,
            "get-bundle": cmd_campaign_get_bundle,
            "apply-bundle": cmd_campaign_apply_bundle,
            "copy-settings": cmd_campaign_copy_settings,
        },
        "schedule-templates": {
            "list": cmd_schedule_template_list,
            "create": cmd_schedule_template_create,
            "update": cmd_schedule_template_update,
            "delete": cmd_schedule_template_delete,
        },
        "subsequences": {
            "list": cmd_subsequence_list,
            "details": cmd_subsequence_details,
            "create": cmd_subsequence_create,
            "update": cmd_subsequence_update,
        },
        "leads": {
            "add": cmd_leads_add,
            "update": cmd_leads_update,
            "delete": cmd_leads_delete,
        },
        "lead-lists": {
            "list": cmd_lead_list_list,
            "create": cmd_lead_list_create,
            "add-leads": cmd_lead_list_add_leads,
            "get-leads": cmd_lead_list_get_leads,
            "update": cmd_lead_list_update,
            "add-to-campaign": cmd_lead_list_add_to_campaign,
            "delete": cmd_lead_list_delete,
        },
        "accounts": {
            "list": cmd_account_list,
            "warmup": cmd_account_warmup,
        },
        "inbox": {
            "list": cmd_inbox_list,
            "send": cmd_inbox_send,
            "mark-read": cmd_inbox_mark_read,
            "unread-count": cmd_inbox_unread,
            "search": cmd_inbox_search,
        },
        "tags": {"list": cmd_tag_list},
        "webhooks": {
            "list": cmd_webhook_list,
            "subscribe": cmd_webhook_subscribe,
            "unsubscribe": cmd_webhook_unsubscribe,
        },
        "blocklist": {
            "add": cmd_blocklist_add,
            "get": cmd_blocklist_get,
            "delete": cmd_blocklist_delete,
        },
    }

    cmd = dispatch.get(args.command)
    if isinstance(cmd, dict):
        cmd = cmd.get(args.action)
    if cmd:
        cmd(args)
    else:
        p.print_help()

if __name__ == "__main__":
    main()
