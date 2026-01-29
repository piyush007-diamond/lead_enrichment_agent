from execution.date_parser import parse_relative_date

print("Testing 'next friday'...")
result = parse_relative_date("next friday")
print(f"Success: {result.success}")
print(f"Date: {result.date}")
print(f"Error: {result.error}")
