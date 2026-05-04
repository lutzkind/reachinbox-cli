# ReachInbox CLI

Full programmatic access to [ReachInbox](https://app.reachinbox.ai) via the self-hosted proxy. No API key needed — uses your existing proxy session.

## Quick Start

```bash
pip install reachinbox-cli

# Or just download the single script:
curl -o /usr/local/bin/reachinbox https://raw.githubusercontent.com/lutzkind/reachinbox-cli/main/reachinbox.py
chmod +x /usr/local/bin/reachinbox
```

```bash
reachinbox health
```

## Configuration

Set the proxy URL via environment variable (defaults to the internal Docker proxy):

```bash
export REACHINBOX_PROXY_URL=http://172.30.0.3:3000
```

## Usage

### Campaigns
```
reachinbox campaigns list [--limit 50] [--filter all] [--sort newest]
reachinbox campaigns create "Campaign Name"
reachinbox campaigns start --campaign-id 123
reachinbox campaigns pause --campaign-id 123
reachinbox campaigns update --campaign-id 123 --name "New Name"
reachinbox campaigns analytics --campaign-id 123
reachinbox campaigns total-analytics [--start-date 2024-01-01] [--end-date 2024-12-31]
reachinbox campaigns details --campaign-id 123
reachinbox campaigns options --campaign-id 123
reachinbox campaigns schedule --campaign-id 123
reachinbox campaigns accounts --campaign-id 123
reachinbox campaigns account-errors --campaign-id 123
reachinbox campaigns delete --campaign-id 123
reachinbox campaigns save-options --campaign-id 123 --payload '{"dailyLimit": 100}'
reachinbox campaigns save-schedule --campaign-id 123 --payload '{"startDate": "2024-01-01"}'
reachinbox campaigns sequences-get --campaign-id 123
reachinbox campaigns sequences-save --campaign-id 123 --sequences '[...]'
reachinbox campaigns get-bundle --campaign-id 123
reachinbox campaigns apply-bundle --campaign-id 123 --bundle-file bundle.json
reachinbox campaigns copy-settings --source-campaign-id 123 --target-campaign-id 456
```

### Schedule Templates
```
reachinbox schedule-templates list
reachinbox schedule-templates create --payload '{"name": "My Template"}'
reachinbox schedule-templates update --template-id 1 --payload '{"name": "Updated"}'
reachinbox schedule-templates delete --template-id 1
```

### Subsequences
```
reachinbox subsequences list --campaign-id 123
reachinbox subsequences details --subsequence-id 456
reachinbox subsequences create --campaign-id 123 --name "Follow-up" --subject "Re: ..." --body "Email body"
reachinbox subsequences update --subsequence-id 456 --name "New Name" --body "Updated body"
```

### Leads
```
reachinbox leads add --campaign-id 123 --leads '[{"email": "test@example.com", "firstName": "John"}]'
reachinbox leads update --campaign-id 123 --email "test@example.com" --firstName "Jane"
reachinbox leads delete --campaign-id 123 --emails '["test@example.com"]'
```

### Lead Lists
```
reachinbox lead-lists list
reachinbox lead-lists create --name "My List"
reachinbox lead-lists add-leads --list-id 456 --leads '[{"email": "test@example.com"}]'
reachinbox lead-lists get-leads --list-id 456
reachinbox lead-lists update --list-id 456 --name "Renamed List"
reachinbox lead-lists add-to-campaign --list-id 456 --campaign-id 123
reachinbox lead-lists delete --list-id 456
```

### Email Accounts
```
reachinbox accounts list
reachinbox accounts warmup
```

### Inbox (Onebox)
```
reachinbox inbox list [--page 1] [--limit 20]
reachinbox inbox send --thread-id "abc123" --body "Thanks!" [--subject "Re: ..."]
reachinbox inbox mark-read
reachinbox inbox unread-count
reachinbox inbox search --query "keyword"
```

### Tags
```
reachinbox tags list
```

### Webhooks
```
reachinbox webhooks list
reachinbox webhooks subscribe --campaign-id 123 --event REPLY_RECEIVED --callback-url https://example.com/hook
reachinbox webhooks unsubscribe --id "sub_abc" [or --campaign-id 123 --event REPLY_RECEIVED --callback-url ...]
```

### Blocklist
```
reachinbox blocklist add --emails '["spam@example.com"]'
reachinbox blocklist get [--table emails]
reachinbox blocklist delete --table emails --ids '["spam@example.com"]'
```

## License

MIT
