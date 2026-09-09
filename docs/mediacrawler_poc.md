# MediaCrawler isolated PoC

This third-party repository is kept at
`tools/mediacrawler/MediaCrawler-main` for non-commercial learning and Demo
validation only. It is not imported by the AI Marketing Assistant backend.

## Locked scope

- Platform: Xiaohongshu only
- Mode: keyword search
- Keyword: `兽设`
- Maximum records: 20
- Concurrency: 1
- Output: local JSONL
- Proxy: disabled
- Comments: disabled
- Media downloads: disabled
- Word cloud: disabled
- Saved login state: disabled
- CDP connection to the user's existing browser: disabled

The tool may require QR-code login even when the ordinary website exposes some
content to visitors. Login is completed by the user. Do not put account
credentials or cookies in configuration files.

## Stop conditions

Do not run while an earlier access restriction is still active. Stop the run
if the platform displays account abnormality, CAPTCHA, access restriction, or
requires verification. Do not enable proxies, account pools, stealth changes,
or automated verification handling.

## Run later

After the earlier platform restriction has cleared, run the guarded project
wrapper from the AI Marketing Assistant root:

```bash
./scripts/run_mediacrawler_poc.sh
```

The wrapper supplies the isolated Python, cache, and Chromium paths. The user
must complete QR login personally if requested. The wrapper does not automate
CAPTCHA or verification handling.

Review the generated JSONL before copying any records into the main project's
`data/` directory. Missing or blocked results must not be converted to zero or
replaced with unlabeled mock data.
