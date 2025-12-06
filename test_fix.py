from api_migration_system.core.api_diff_analyzer import APIDiffAnalyzer

analyzer = APIDiffAnalyzer()

old_code = """
def old_api(param):
    return param * 2
"""
new_code = """
def new_api(param, scale=1):
    return param * 2 * scale
"""

old_entities = analyzer.analyze_source_code(old_code)
new_entities = analyzer.analyze_source_code(new_code)

print("Old entities:", [e.name for e in old_entities])
print("New entities:", [e.name for e in new_entities])

old_key = analyzer._entity_key(old_entities[0])
new_key = analyzer._entity_key(new_entities[0])

print(f"Old key: {old_key}")
print(f"New key: {new_key}")

similarity = analyzer._calculate_similarity(new_key, old_key)
print(f"Similarity: {similarity}")

diffs = analyzer.compare_versions(old_entities, new_entities)
print(f"Number of diffs: {len(diffs)}")
for diff in diffs:
    print(f"  Type: {diff.change_type}, Description: {diff.description}")