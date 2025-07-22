#!/usr/bin/env python3
"""Demonstrate clean output format for OptionEAE parsing"""

# Simulate the parsing results
exercises_found = [
    {'symbol': '616P', 'date': '20250714', 'type': 'Expiration'},
    {'symbol': '621C', 'date': '20250714', 'type': 'Expiration'},
    {'symbol': '622P', 'date': '20250715', 'type': 'Assignment'},
    {'symbol': '624C', 'date': '20250715', 'type': 'Expiration'},
    {'symbol': '620P', 'date': '20250716', 'type': 'Expiration'},
    {'symbol': '626C', 'date': '20250716', 'type': 'Expiration'},
    {'symbol': '624P', 'date': '20250717', 'type': 'Expiration'},
    {'symbol': '628C', 'date': '20250717', 'type': 'Expiration'},
    {'symbol': '626P', 'date': '20250718', 'type': 'Expiration'},
    {'symbol': '628C', 'date': '20250718', 'type': 'Expiration'},
]

# Simulate summary counts
total_records = 50  # Example: 50 total OptionEAE records
spy_options = 10
spy_stocks = 1
other_records = 39

print("\nCLEANER OUTPUT FORMAT DEMO")
print("="*50)

# Summary table
print("\n  ┌─────────────────────────────────────────────┐")
print("  │         OptionEAE Records Summary           │")
print("  ├─────────────────────────────────────────────┤")
print(f"  │ SPY Options:     {spy_options:3d} records                │")
print(f"  │ SPY Stock:       {spy_stocks:3d} records                │")
print(f"  │ Other:           {other_records:3d} records                │")
print(f"  │ Total:           {total_records:3d} records                │")
print("  └─────────────────────────────────────────────┘")

# Group by date
by_date = {}
for ex in exercises_found:
    date = ex['date']
    if date not in by_date:
        by_date[date] = {'assignments': [], 'expirations': [], 'exercises': [], 'pending': []}
    
    if ex['type'] == 'Assignment':
        by_date[date]['assignments'].append(ex['symbol'])
    elif ex['type'] == 'Expiration':
        by_date[date]['expirations'].append(ex['symbol'])
    elif ex['type'] == 'Exercise':
        by_date[date]['exercises'].append(ex['symbol'])
    else:
        by_date[date]['pending'].append(ex['symbol'])

# Display summary table
print("\n  ┌────────────┬───────────────────────────────────┐")
print("  │    Date    │         Option Events             │")
print("  ├────────────┼───────────────────────────────────┤")

for date in sorted(by_date.keys()):
    events = by_date[date]
    event_strs = []
    
    if events['assignments']:
        event_strs.append(f"✅ ASSIGN: {', '.join(events['assignments'])}")
    
    if events['expirations']:
        event_strs.append(f"⏰ EXPIRE: {', '.join(events['expirations'])}")
    
    if events['exercises']:
        event_strs.append(f"🏃 EXERCISE: {', '.join(events['exercises'])}")
    
    if events['pending']:
        event_strs.append(f"⚠️  PENDING: {', '.join(events['pending'])}")
    
    # Format date as MM/DD
    date_formatted = f"{date[4:6]}/{date[6:8]}"
    event_str = ', '.join(event_strs) if event_strs else "No events"
    
    # Truncate if too long
    if len(event_str) > 33:
        event_str = event_str[:30] + "..."
    
    print(f"  │ {date_formatted:^10} │ {event_str:<33} │")

print("  └────────────┴───────────────────────────────────┘")

# Summary counts
total_assignments = sum(len(ex['assignments']) for ex in by_date.values())
total_expirations = sum(len(ex['expirations']) for ex in by_date.values())
total_exercises = sum(len(ex['exercises']) for ex in by_date.values())
total_pending = sum(len(ex['pending']) for ex in by_date.values())

print(f"\n  Summary: {total_assignments} assignments, {total_expirations} expirations, "
      f"{total_exercises} exercises, {total_pending} pending")

print("\n" + "="*50)
print("BENEFITS OF THIS FORMAT:")
print("- No verbose XML attribute dumps")
print("- Clean tabular presentation")
print("- Events grouped by date")
print("- Clear visual indicators (✅ ⏰ 🏃 ⚠️)")
print("- One-line summary at the end")