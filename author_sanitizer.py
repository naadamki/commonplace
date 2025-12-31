"""
Author Name Sanitizer - Interactive script to clean up and standardize author names.

Features:
- Format standardization (C. S. Lewis, Title Case, Scripture references)
- Duplicate author merging
- Whitelist/blacklist management
- Change history and undo capability
- Validation and export of changes
- Session management
"""

from db import DB, NotFoundError, DuplicateError
from models import Author
import re
import json
from datetime import datetime
from pathlib import Path


class ChangeLog:
    """Manage change history with undo capability"""
    
    def __init__(self, log_file: str = "author_changes.json"):
        self.log_file = Path(log_file)
        self.changes = []
        self.load()
    
    def load(self):
        """Load existing changelog"""
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r') as f:
                    data = json.load(f)
                    self.changes = data.get('changes', [])
            except:
                self.changes = []
        else:
            self.changes = []
    
    def save(self):
        """Save changelog to disk"""
        with open(self.log_file, 'w') as f:
            json.dump({
                'changes': self.changes,
                'last_updated': datetime.now().isoformat()
            }, f, indent=2)
    
    def add(self, change_type: str, author_id: int, old_name: str, new_name: str, 
            merged_with: str = None, timestamp: str = None):
        """Add a change to the log"""
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        change = {
            'timestamp': timestamp,
            'type': change_type,  # RENAMED, MERGED, DELETED
            'author_id': author_id,
            'old_name': old_name,
            'new_name': new_name,
            'merged_with': merged_with
        }
        self.changes.append(change)
        self.save()
    
    def get_latest(self, count: int = 10):
        """Get most recent changes"""
        return self.changes[-count:]
    
    def get_by_type(self, change_type: str):
        """Get changes of a specific type"""
        return [c for c in self.changes if c['type'] == change_type]
    
    def export(self, filename: str = "author_changes_export.json"):
        """Export full changelog"""
        with open(filename, 'w') as f:
            json.dump({
                'total_changes': len(self.changes),
                'timestamp': datetime.now().isoformat(),
                'changes': self.changes
            }, f, indent=2)
        print(f"✓ Exported {len(self.changes)} changes to {filename}")


class NameValidator:
    """Validate author names against formatting rules"""
    
    # Patterns for different name types
    PATTERNS = {
        'abbreviation': r'^([A-Z]\. )+[A-Z][a-z]+(\s*\([^)]+\))?
    
    @staticmethod
    def validate(name: str) -> tuple[bool, str]:
        """
        Validate if a name matches expected format
        
        Returns:
            (is_valid, pattern_matched)
        """
        for pattern_name, pattern in NameValidator.PATTERNS.items():
            if re.match(pattern, name):
                return True, pattern_name
        
        return False, "unknown"
    
    @staticmethod
    def suggest_fixes(name: str) -> list[str]:
        """Suggest what might be wrong with a name"""
        fixes = []
        
        if name != name.strip():
            fixes.append("Remove leading/trailing whitespace")
        
        if '  ' in name:
            fixes.append("Remove extra spaces")
        
        if re.search(r'[a-z]\. [A-Z]', name):
            fixes.append("Lowercase letters should not precede periods in abbreviations")
        
        if re.search(r'([A-Z][a-z]*){3,}', name) and not re.search(r'\s', name):
            fixes.append("Name is missing spaces between parts")
        
        if name.isupper() and len(name) > 1:
            fixes.append("Name is all uppercase - should be title case")
        
        return fixes


class NameWhitelist:
    """Manage known good author names"""
    
    def __init__(self, whitelist_file: str = "author_whitelist.json"):
        self.whitelist_file = Path(whitelist_file)
        self.names = set()
        self.metadata = {}
        self.load()
    
    def load(self):
        """Load whitelist from disk"""
        if self.whitelist_file.exists():
            try:
                with open(self.whitelist_file, 'r') as f:
                    data = json.load(f)
                    self.names = set(data.get('names', []))
                    self.metadata = data.get('metadata', {})
            except:
                self.names = set()
                self.metadata = {}
    
    def save(self):
        """Save whitelist to disk"""
        with open(self.whitelist_file, 'w') as f:
            json.dump({
                'names': sorted(list(self.names)),
                'metadata': self.metadata,
                'count': len(self.names),
                'last_updated': datetime.now().isoformat()
            }, f, indent=2)
    
    def add(self, name: str, notes: str = ""):
        """Add a name to the whitelist"""
        self.names.add(name)
        if notes:
            self.metadata[name] = {'added': datetime.now().isoformat(), 'notes': notes}
        self.save()
    
    def remove(self, name: str):
        """Remove a name from whitelist"""
        self.names.discard(name)
        if name in self.metadata:
            del self.metadata[name]
        self.save()
    
    def is_whitelisted(self, name: str) -> bool:
        """Check if name is whitelisted"""
        return name in self.names
    
    def export(self, filename: str = "author_whitelist_export.json"):
        """Export whitelist"""
        with open(filename, 'w') as f:
            json.dump({
                'names': sorted(list(self.names)),
                'metadata': self.metadata,
                'count': len(self.names),
                'exported': datetime.now().isoformat()
            }, f, indent=2)
        print(f"✓ Exported {len(self.names)} whitelisted names to {filename}")


class NameBlacklist:
    """Manage known bad author name patterns"""
    
    def __init__(self, blacklist_file: str = "author_blacklist.json"):
        self.blacklist_file = Path(blacklist_file)
        self.patterns = []  # List of regex patterns
        self.exact_names = set()
        self.load()
    
    def load(self):
        """Load blacklist from disk"""
        if self.blacklist_file.exists():
            try:
                with open(self.blacklist_file, 'r') as f:
                    data = json.load(f)
                    self.patterns = data.get('patterns', [])
                    self.exact_names = set(data.get('exact_names', []))
            except:
                self.patterns = []
                self.exact_names = set()
    
    def save(self):
        """Save blacklist to disk"""
        with open(self.blacklist_file, 'w') as f:
            json.dump({
                'patterns': self.patterns,
                'exact_names': sorted(list(self.exact_names)),
                'total_patterns': len(self.patterns),
                'total_names': len(self.exact_names),
                'last_updated': datetime.now().isoformat()
            }, f, indent=2)
    
    def add_pattern(self, pattern: str, reason: str = ""):
        """Add a regex pattern to blacklist"""
        self.patterns.append({'pattern': pattern, 'reason': reason})
        self.save()
    
    def add_exact(self, name: str, reason: str = ""):
        """Add an exact name to blacklist"""
        self.exact_names.add(name)
        self.save()
    
    def is_blacklisted(self, name: str) -> tuple[bool, str]:
        """
        Check if name matches blacklist
        
        Returns:
            (is_blacklisted, reason)
        """
        # Check exact matches
        if name in self.exact_names:
            return True, "exact match in blacklist"
        
        # Check patterns
        for item in self.patterns:
            try:
                if re.search(item['pattern'], name):
                    return True, item.get('reason', 'matched pattern')
            except:
                pass
        
        return False, ""
    
    def export(self, filename: str = "author_blacklist_export.json"):
        """Export blacklist"""
        with open(filename, 'w') as f:
            json.dump({
                'patterns': self.patterns,
                'exact_names': sorted(list(self.exact_names)),
                'total_patterns': len(self.patterns),
                'total_names': len(self.exact_names),
                'exported': datetime.now().isoformat()
            }, f, indent=2)
        print(f"✓ Exported blacklist to {filename}")


class AuthorSanitizer:
    """Interactive tool for cleaning and standardizing author names"""
    
    def __init__(self):
        self.db = DB()
        self.changelog = ChangeLog()
        self.whitelist = NameWhitelist()
        self.blacklist = NameBlacklist()
        self.changes_made = []
        self.skipped = []
        self.session_start = datetime.now()
    
    def close(self):
        """Close database connection"""
        self.db.close()
    
    def needs_editing(self):
        """Get all authors marked for editing"""
        return self.db.authors.needs_edit()
    
    def is_likely_garbage(self, name: str) -> tuple[bool, list[str]]:
        """Check if author name looks suspicious/needs attention"""
        issues = []
        
        # Check blacklist first
        is_blacklisted, reason = self.blacklist.is_blacklisted(name)
        if is_blacklisted:
            issues.append(f"blacklist match ({reason})")
        
        # Check whitelist
        if self.whitelist.is_whitelisted(name):
            return False, []  # Whitelisted = good to go
        
        # Check for excessive quotation marks
        if name.count('"') > 2:
            issues.append(f"excessive quotes ({name.count('\"')} found)")
        
        # Check for malformed abbreviations (C.S.Lewis instead of C. S. Lewis)
        if re.search(r'[A-Z]\.[A-Z]\.', name) and not re.search(r'[A-Z]\. [A-Z]\.', name):
            issues.append("improper abbreviation spacing")
        
        # Check for mixed case that suggests garbage
        if re.search(r'[A-Z][a-z]*[A-Z]', name) and not re.search(r'\(', name):
            issues.append("unusual capitalization")
        
        # Check for numbers at start (scripture references)
        if re.match(r'^\d+', name) and not re.match(r'^\d+\s+[A-Za-z]+', name):
            issues.append("possible malformed scripture reference")
        
        # Check for excessive punctuation
        if name.count('.') > 4:
            issues.append("excessive periods")
        
        # Check format validity
        is_valid, pattern = NameValidator.validate(name)
        if not is_valid:
            issues.append(f"doesn't match standard patterns")
        
        return len(issues) > 0, issues
    
    def clean_quotation_marks(self, name: str) -> str:
        """Remove excessive embedded quotation marks, extracting the content"""
        # Pattern: text """""content""""" text -> text (content) text
        match = re.search(r'(\w+)\s+"{2,}(.+?)"{2,}\s+(\w+)', name)
        if match:
            before = match.group(1)
            content = match.group(2).strip()
            after = match.group(3)
            return f"{before} {after} ({content})"
        
        # Just remove quotes if no clear pattern
        return name.replace('"', '')
    
    def format_abbreviations(self, name: str) -> str:
        """Fix abbreviation spacing: C.S. Lewis -> C. S. Lewis"""
        # Find patterns like C.S. and fix to C. S.
        name = re.sub(r'([A-Z])\.([A-Z])\.', r'\1. \2.', name)
        # Fix spacing after abbreviations if needed
        name = re.sub(r'([A-Z]\.) ([A-Z]\.)', r'\1 \2', name)
        return name.strip()
    
    def format_title_case(self, name: str) -> str:
        """Convert to title case, respecting articles and prepositions"""
        # Words that should be lowercase in titles (unless first word)
        lowercase_words = {'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        
        # Preserve parenthetical content
        paren_match = re.match(r'^(.*?)(\(.+\))$', name)
        if paren_match:
            title = paren_match.group(1).strip()
            paren = paren_match.group(2)
            name = title
            preserve_paren = paren
        else:
            preserve_paren = None
        
        # Split and process words
        words = name.split()
        result = []
        
        for i, word in enumerate(words):
            if i == 0 or word.lower() not in lowercase_words:
                result.append(word.capitalize())
            else:
                result.append(word.lower())
        
        final = ' '.join(result)
        if preserve_paren:
            final = f"{final} {preserve_paren}"
        
        return final
    
    def format_scripture_reference(self, name: str) -> str:
        """Format scripture references: 1 Kings 1:12-14 or 1 Kings 1 (NIV)"""
        # Already well-formatted
        if re.match(r'^\d+\s+[A-Za-z]+\s+\d+', name):
            return name
        return name
    
    def suggest_format(self, name: str) -> str:
        """Suggest how the name should be formatted"""
        original = name
        
        # Clean garbage quotation marks first
        if '"""' in name or '""""' in name:
            name = self.clean_quotation_marks(name)
        
        # Check if it's a scripture reference
        if re.match(r'^\d+\s+[A-Z]', name):
            return self.format_scripture_reference(name)
        
        # Check if it looks like a title (multiple capitals, or keywords)
        is_title = (
            name.isupper() or 
            re.search(r'\b(The|A|An|And|Or)\b', name) or
            ': ' in name or  # Subtitles
            name.count(' ') > 2 and sum(1 for c in name if c.isupper()) > 2
        )
        
        if is_title and not re.match(r'^[A-Z]\.\s', name):  # Not an abbreviation
            return self.format_title_case(name)
        
        # Regular name - fix abbreviations
        return self.format_abbreviations(name)
    
    def print_author(self, author: Author) -> None:
        """Pretty print author info"""
        print(f"\n{'='*80}")
        print(f"ID: {author.id}")
        print(f"Name: {author.name}")
        
        # Validate current name
        is_valid, pattern = NameValidator.validate(author.name)
        if is_valid:
            print(f"Status: ✓ Valid ({pattern})")
        else:
            print(f"Status: ✗ Invalid format")
            fixes = NameValidator.suggest_fixes(author.name)
            if fixes:
                print("Suggested fixes:")
                for fix in fixes:
                    print(f"  - {fix}")
        
        if author.birth_year or author.death_year:
            years = f"{author.birth_year or '?'}-{author.death_year or '?'}"
            print(f"Years: {years}")
        if author.profession:
            print(f"Profession: {author.profession}")
        if author.nationality:
            print(f"Nationality: {author.nationality}")
        print(f"Quotes: {len(author.quotes)}")
        if author.quotes:
            print(f"Sample quote: {author.quotes[0].text[:70]}...")
        print(f"{'='*80}")
    
    def author_exists(self, name: str) -> bool:
        """Check if author with this name already exists"""
        try:
            return self.db.authors.get_by_name(name) is not None
        except:
            return False
    
    def merge_authors(self, from_author: Author, to_author: Author) -> None:
        """Move all quotes from one author to another, then delete the from_author"""
        print(f"\nMerging {len(from_author.quotes)} quotes from '{from_author.name}' to '{to_author.name}'...")
        
        # Move quotes
        for quote in from_author.quotes[:]:  # Use slice to avoid modification during iteration
            quote.author = to_author
        
        self.db.commit()
        
        # Delete the old author
        old_id = from_author.id
        self.db.session.delete(from_author)
        self.db.commit()
        
        # Log the merge
        self.changelog.add('MERGED', old_id, from_author.name, to_author.name, merged_with=to_author.name)
        
        print(f"✓ Merge complete!")
    
    def process_author(self, author: Author) -> None:
        """Interactive processing for a single author"""
        is_garbage, issues = self.is_likely_garbage(author.name)
        
        if is_garbage:
            print(f"\n⚠ Issues detected: {', '.join(issues)}")
        
        self.print_author(author)
        
        # Show suggestion
        suggestion = self.suggest_format(author.name)
        if suggestion != author.name:
            print(f"\nSuggested format: {suggestion}")
        else:
            print(f"\nNo format changes suggested.")
        
        while True:
            print("\nOptions:")
            print("  [1] Keep as is")
            if suggestion != author.name:
                print("  [2] Accept suggestion")
            print("  [3] Manual edit")
            print("  [4] Add to whitelist (skip)")
            print("  [5] Add to blacklist")
            print("  [6] Delete author and all quotes")
            print("  [7] Skip this author")
            
            choice = input("\nChoose option: ").strip()
            
            if choice == '1':
                self.skipped.append(author.name)
                print("✓ Keeping as is")
                return
            
            elif choice == '2' and suggestion != author.name:
                self._apply_change(author, suggestion)
                return
            
            elif choice == '3':
                new_name = input("Enter correct author name: ").strip()
                if new_name:
                    self._apply_change(author, new_name)
                    return
                else:
                    print("Name cannot be empty")
            
            elif choice == '4':
                self.whitelist.add(author.name, "User approved during sanitization")
                print(f"✓ Added '{author.name}' to whitelist")
                self.skipped.append(author.name)
                return
            
            elif choice == '5':
                reason = input("Reason for blacklisting: ").strip()
                self.blacklist.add_exact(author.name, reason or "Garbage/spam author")
                print(f"✓ Added '{author.name}' to blacklist")
                
                delete = input("Delete this author and quotes? (yes/no): ").strip().lower()
                if delete == 'yes':
                    self.db.session.delete(author)
                    self.db.commit()
                    print(f"✓ Deleted")
                    self.changes_made.append(f"DELETED: {author.name}")
                return
            
            elif choice == '6':
                confirm = input(f"Delete '{author.name}' and its {len(author.quotes)} quotes? (yes/no): ").strip().lower()
                if confirm == 'yes':
                    self.db.session.delete(author)
                    self.db.commit()
                    print(f"✓ Deleted")
                    self.changes_made.append(f"DELETED: {author.name}")
                    self.changelog.add('DELETED', author.id, author.name, "")
                    return
                else:
                    print("Cancelled")
            
            elif choice == '7':
                self.skipped.append(author.name)
                print("✓ Skipped")
                return
            
            else:
                print("Invalid option")
    
    def _apply_change(self, author: Author, new_name: str) -> None:
        """Apply a name change, handling duplicates"""
        new_name = new_name.strip()
        
        if new_name == author.name:
            print("No change made")
            return
        
        # Check if new name already exists
        existing = self.db.authors.get_by_name(new_name)
        
        if existing and existing.id != author.id:
            print(f"\n⚠ Author '{new_name}' already exists!")
            print(f"  Existing author has {len(existing.quotes)} quotes")
            print(f"  Current author '{author.name}' has {len(author.quotes)} quotes")
            
            merge_choice = input("\nMerge these authors? (yes/no): ").strip().lower()
            if merge_choice == 'yes':
                self.merge_authors(author, existing)
                self.changes_made.append(f"MERGED: '{author.name}' -> '{new_name}'")
            else:
                print("Cancelled - no changes made")
            return
        
        # Safe to rename
        old_name = author.name
        author.name = new_name
        author.unmark_for_edit()  # Remove the edit flag
        self.db.commit()
        
        # Log change
        self.changelog.add('RENAMED', author.id, old_name, new_name)
        
        print(f"✓ Changed: '{old_name}' -> '{new_name}'")
        self.changes_made.append(f"RENAMED: '{old_name}' -> '{new_name}'")
    
    def undo_last_change(self):
        """Undo the most recent change"""
        recent = self.changelog.get_latest(1)
        if not recent:
            print("No changes to undo")
            return
        
        change = recent[0]
        print(f"\nUndoing: {change}")
        print("Note: Undo is not yet implemented in the database layer")
        print("You would need to manually revert this change or restore from backup")
    
    def run_interactive(self):
        """Main interactive loop"""
        authors = self.needs_editing()
        
        if not authors:
            print("✓ No authors need editing!")
            return
        
        print(f"\nFound {len(authors)} authors needing editing")
        print("="*80)
        
        for i, author in enumerate(authors, 1):
            print(f"\n[{i}/{len(authors)}]")
            self.process_author(author)
        
        self.print_summary()
    
    def run_batch(self, auto_fix=False):
        """
        Run in batch mode - optionally auto-fix obvious issues
        
        Args:
            auto_fix: If True, automatically apply suggestions without confirmation
        """
        authors = self.needs_editing()
        
        if not authors:
            print("✓ No authors need editing!")
            return
        
        print(f"\nProcessing {len(authors)} authors...")
        print("="*80)
        
        for i, author in enumerate(authors, 1):
            is_garbage, issues = self.is_likely_garbage(author.name)
            suggestion = self.suggest_format(author.name)
            
            if suggestion != author.name:
                if auto_fix:
                    print(f"[{i}/{len(authors)}] Auto-fixing: {author.name}")
                    if not self.author_exists(suggestion):
                        self._apply_change(author, suggestion)
                    else:
                        existing = self.db.authors.get_by_name(suggestion)
                        self.merge_authors(author, existing)
                else:
                    print(f"[{i}/{len(authors)}] Review needed: {author.name}")
        
        self.print_summary()
    
    def print_summary(self):
        """Print summary of changes"""
        print(f"\n{'='*80}")
        print("SUMMARY")
        print(f"{'='*80}")
        print(f"Session started: {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Changes made: {len(self.changes_made)}")
        for change in self.changes_made:
            print(f"  ✓ {change}")
        
        if self.skipped:
            print(f"\nSkipped: {len(self.skipped)}")
            for name in self.skipped[:5]:
                print(f"  - {name}")
            if len(self.skipped) > 5:
                print(f"  ... and {len(self.skipped) - 5} more")
        
        # Export options
        print("\nExport options:")
        export_choice = input("Export changelog? (yes/no): ").strip().lower()
        if export_choice == 'yes':
            self.changelog.export()
        
        export_choice = input("Export whitelist? (yes/no): ").strip().lower()
        if export_choice == 'yes':
            self.whitelist.export()
        
        export_choice = input("Export blacklist? (yes/no): ").strip().lower()
        if export_choice == 'yes':
            self.blacklist.export()


def main():
    """Main entry point"""
    print("Author Name Sanitizer")
    print("="*80)
    
    sanitizer = AuthorSanitizer()
    
    try:
        while True:
            print("\nModes:")
            print("  [1] Interactive mode (review each author)")
            print("  [2] Batch mode (auto-fix obvious issues)")
            print("  [3] View recent changes")
            print("  [4] Manage whitelist")
            print("  [5] Manage blacklist")
            print("  [6] Exit")
            
            choice = input("\nChoose mode: ").strip()
            
            if choice == '1':
                sanitizer.run_interactive()
                break
            
            elif choice == '2':
                confirm = input("Auto-fix obvious issues? (yes/no): ").strip().lower()
                if confirm == 'yes':
                    sanitizer.run_batch(auto_fix=True)
                    break
                else:
                    print("Cancelled")
            
            elif choice == '3':
                recent = sanitizer.changelog.get_latest(10)
                print(f"\nRecent changes ({len(recent)} shown):")
                for change in recent:
                    print(f"  {change['timestamp']}: {change['type']} - {change['old_name']} -> {change['new_name']}")
            
            elif choice == '4':
                print("\nWhitelist Management:")
                print("  [1] View whitelist")
                print("  [2] Add to whitelist")
                print("  [3] Remove from whitelist")
                print("  [4] Back")
                sub_choice = input("Choose: ").strip()
                
                if sub_choice == '1':
                    if sanitizer.whitelist.names:
                        for name in sorted(list(sanitizer.whitelist.names))[:20]:
                            print(f"  - {name}")
                        if len(sanitizer.whitelist.names) > 20:
                            print(f"  ... and {len(sanitizer.whitelist.names) - 20} more")
                    else:
                        print("  Whitelist is empty")
                
                elif sub_choice == '2':
                    name = input("Enter author name: ").strip()
                    notes = input("Notes (optional): ").strip()
                    sanitizer.whitelist.add(name, notes)
                    print(f"✓ Added '{name}' to whitelist")
                
                elif sub_choice == '3':
                    name = input("Enter author name to remove: ").strip()
                    sanitizer.whitelist.remove(name)
                    print(f"✓ Removed '{name}' from whitelist")
            
            elif choice == '5':
                print("\nBlacklist Management:")
                print("  [1] View blacklist")
                print("  [2] Add exact name")
                print("  [3] Add pattern")
                print("  [4] Back")
                sub_choice = input("Choose: ").strip()
                
                if sub_choice == '1':
                    if sanitizer.blacklist.exact_names:
                        print("Exact names:")
                        for name in sorted(list(sanitizer.blacklist.exact_names))[:10]:
                            print(f"  - {name}")
                    if sanitizer.blacklist.patterns:
                        print("Patterns:")
                        for item in sanitizer.blacklist.patterns[:5]:
                            print(f"  - {item['pattern']} ({item.get('reason', 'N/A')})")
                
                elif sub_choice == '2':
                    name = input("Enter author name: ").strip()
                    reason = input("Reason: ").strip()
                    sanitizer.blacklist.add_exact(name, reason)
                    print(f"✓ Added '{name}' to blacklist")
                
                elif sub_choice == '3':
                    pattern = input("Enter regex pattern: ").strip()
                    reason = input("Reason: ").strip()
                    sanitizer.blacklist.add_pattern(pattern, reason)
                    print(f"✓ Added pattern to blacklist")
            
            elif choice == '6':
                print("Exiting...")
                break
            
            else:
                print("Invalid option")
    
    finally:
        sanitizer.close()


if __name__ == "__main__":
    main(),  # C. S. Lewis or C. Lewis
        'name_with_middle_initial': r'^[A-Z][a-z]+\s+[A-Z]\.\s+[A-Z][a-z]+(\s*\([^)]+\))?
    
    @staticmethod
    def validate(name: str) -> tuple[bool, str]:
        """
        Validate if a name matches expected format
        
        Returns:
            (is_valid, pattern_matched)
        """
        for pattern_name, pattern in NameValidator.PATTERNS.items():
            if re.match(pattern, name):
                return True, pattern_name
        
        return False, "unknown"
    
    @staticmethod
    def suggest_fixes(name: str) -> list[str]:
        """Suggest what might be wrong with a name"""
        fixes = []
        
        if name != name.strip():
            fixes.append("Remove leading/trailing whitespace")
        
        if '  ' in name:
            fixes.append("Remove extra spaces")
        
        if re.search(r'[a-z]\. [A-Z]', name):
            fixes.append("Lowercase letters should not precede periods in abbreviations")
        
        if re.search(r'([A-Z][a-z]*){3,}', name) and not re.search(r'\s', name):
            fixes.append("Name is missing spaces between parts")
        
        if name.isupper() and len(name) > 1:
            fixes.append("Name is all uppercase - should be title case")
        
        return fixes


class NameWhitelist:
    """Manage known good author names"""
    
    def __init__(self, whitelist_file: str = "author_whitelist.json"):
        self.whitelist_file = Path(whitelist_file)
        self.names = set()
        self.metadata = {}
        self.load()
    
    def load(self):
        """Load whitelist from disk"""
        if self.whitelist_file.exists():
            try:
                with open(self.whitelist_file, 'r') as f:
                    data = json.load(f)
                    self.names = set(data.get('names', []))
                    self.metadata = data.get('metadata', {})
            except:
                self.names = set()
                self.metadata = {}
    
    def save(self):
        """Save whitelist to disk"""
        with open(self.whitelist_file, 'w') as f:
            json.dump({
                'names': sorted(list(self.names)),
                'metadata': self.metadata,
                'count': len(self.names),
                'last_updated': datetime.now().isoformat()
            }, f, indent=2)
    
    def add(self, name: str, notes: str = ""):
        """Add a name to the whitelist"""
        self.names.add(name)
        if notes:
            self.metadata[name] = {'added': datetime.now().isoformat(), 'notes': notes}
        self.save()
    
    def remove(self, name: str):
        """Remove a name from whitelist"""
        self.names.discard(name)
        if name in self.metadata:
            del self.metadata[name]
        self.save()
    
    def is_whitelisted(self, name: str) -> bool:
        """Check if name is whitelisted"""
        return name in self.names
    
    def export(self, filename: str = "author_whitelist_export.json"):
        """Export whitelist"""
        with open(filename, 'w') as f:
            json.dump({
                'names': sorted(list(self.names)),
                'metadata': self.metadata,
                'count': len(self.names),
                'exported': datetime.now().isoformat()
            }, f, indent=2)
        print(f"✓ Exported {len(self.names)} whitelisted names to {filename}")


class NameBlacklist:
    """Manage known bad author name patterns"""
    
    def __init__(self, blacklist_file: str = "author_blacklist.json"):
        self.blacklist_file = Path(blacklist_file)
        self.patterns = []  # List of regex patterns
        self.exact_names = set()
        self.load()
    
    def load(self):
        """Load blacklist from disk"""
        if self.blacklist_file.exists():
            try:
                with open(self.blacklist_file, 'r') as f:
                    data = json.load(f)
                    self.patterns = data.get('patterns', [])
                    self.exact_names = set(data.get('exact_names', []))
            except:
                self.patterns = []
                self.exact_names = set()
    
    def save(self):
        """Save blacklist to disk"""
        with open(self.blacklist_file, 'w') as f:
            json.dump({
                'patterns': self.patterns,
                'exact_names': sorted(list(self.exact_names)),
                'total_patterns': len(self.patterns),
                'total_names': len(self.exact_names),
                'last_updated': datetime.now().isoformat()
            }, f, indent=2)
    
    def add_pattern(self, pattern: str, reason: str = ""):
        """Add a regex pattern to blacklist"""
        self.patterns.append({'pattern': pattern, 'reason': reason})
        self.save()
    
    def add_exact(self, name: str, reason: str = ""):
        """Add an exact name to blacklist"""
        self.exact_names.add(name)
        self.save()
    
    def is_blacklisted(self, name: str) -> tuple[bool, str]:
        """
        Check if name matches blacklist
        
        Returns:
            (is_blacklisted, reason)
        """
        # Check exact matches
        if name in self.exact_names:
            return True, "exact match in blacklist"
        
        # Check patterns
        for item in self.patterns:
            try:
                if re.search(item['pattern'], name):
                    return True, item.get('reason', 'matched pattern')
            except:
                pass
        
        return False, ""
    
    def export(self, filename: str = "author_blacklist_export.json"):
        """Export blacklist"""
        with open(filename, 'w') as f:
            json.dump({
                'patterns': self.patterns,
                'exact_names': sorted(list(self.exact_names)),
                'total_patterns': len(self.patterns),
                'total_names': len(self.exact_names),
                'exported': datetime.now().isoformat()
            }, f, indent=2)
        print(f"✓ Exported blacklist to {filename}")


class AuthorSanitizer:
    """Interactive tool for cleaning and standardizing author names"""
    
    def __init__(self):
        self.db = DB()
        self.changelog = ChangeLog()
        self.whitelist = NameWhitelist()
        self.blacklist = NameBlacklist()
        self.changes_made = []
        self.skipped = []
        self.session_start = datetime.now()
    
    def close(self):
        """Close database connection"""
        self.db.close()
    
    def needs_editing(self):
        """Get all authors marked for editing"""
        return self.db.authors.needs_edit()
    
    def is_likely_garbage(self, name: str) -> tuple[bool, list[str]]:
        """Check if author name looks suspicious/needs attention"""
        issues = []
        
        # Check blacklist first
        is_blacklisted, reason = self.blacklist.is_blacklisted(name)
        if is_blacklisted:
            issues.append(f"blacklist match ({reason})")
        
        # Check whitelist
        if self.whitelist.is_whitelisted(name):
            return False, []  # Whitelisted = good to go
        
        # Check for excessive quotation marks
        if name.count('"') > 2:
            issues.append(f"excessive quotes ({name.count('\"')} found)")
        
        # Check for malformed abbreviations (C.S.Lewis instead of C. S. Lewis)
        if re.search(r'[A-Z]\.[A-Z]\.', name) and not re.search(r'[A-Z]\. [A-Z]\.', name):
            issues.append("improper abbreviation spacing")
        
        # Check for mixed case that suggests garbage
        if re.search(r'[A-Z][a-z]*[A-Z]', name) and not re.search(r'\(', name):
            issues.append("unusual capitalization")
        
        # Check for numbers at start (scripture references)
        if re.match(r'^\d+', name) and not re.match(r'^\d+\s+[A-Za-z]+', name):
            issues.append("possible malformed scripture reference")
        
        # Check for excessive punctuation
        if name.count('.') > 4:
            issues.append("excessive periods")
        
        # Check format validity
        is_valid, pattern = NameValidator.validate(name)
        if not is_valid:
            issues.append(f"doesn't match standard patterns")
        
        return len(issues) > 0, issues
    
    def clean_quotation_marks(self, name: str) -> str:
        """Remove excessive embedded quotation marks, extracting the content"""
        # Pattern: text """""content""""" text -> text (content) text
        match = re.search(r'(\w+)\s+"{2,}(.+?)"{2,}\s+(\w+)', name)
        if match:
            before = match.group(1)
            content = match.group(2).strip()
            after = match.group(3)
            return f"{before} {after} ({content})"
        
        # Just remove quotes if no clear pattern
        return name.replace('"', '')
    
    def format_abbreviations(self, name: str) -> str:
        """Fix abbreviation spacing: C.S. Lewis -> C. S. Lewis"""
        # Find patterns like C.S. and fix to C. S.
        name = re.sub(r'([A-Z])\.([A-Z])\.', r'\1. \2.', name)
        # Fix spacing after abbreviations if needed
        name = re.sub(r'([A-Z]\.) ([A-Z]\.)', r'\1 \2', name)
        return name.strip()
    
    def format_title_case(self, name: str) -> str:
        """Convert to title case, respecting articles and prepositions"""
        # Words that should be lowercase in titles (unless first word)
        lowercase_words = {'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        
        # Preserve parenthetical content
        paren_match = re.match(r'^(.*?)(\(.+\))$', name)
        if paren_match:
            title = paren_match.group(1).strip()
            paren = paren_match.group(2)
            name = title
            preserve_paren = paren
        else:
            preserve_paren = None
        
        # Split and process words
        words = name.split()
        result = []
        
        for i, word in enumerate(words):
            if i == 0 or word.lower() not in lowercase_words:
                result.append(word.capitalize())
            else:
                result.append(word.lower())
        
        final = ' '.join(result)
        if preserve_paren:
            final = f"{final} {preserve_paren}"
        
        return final
    
    def format_scripture_reference(self, name: str) -> str:
        """Format scripture references: 1 Kings 1:12-14 or 1 Kings 1 (NIV)"""
        # Already well-formatted
        if re.match(r'^\d+\s+[A-Za-z]+\s+\d+', name):
            return name
        return name
    
    def suggest_format(self, name: str) -> str:
        """Suggest how the name should be formatted"""
        original = name
        
        # Clean garbage quotation marks first
        if '"""' in name or '""""' in name:
            name = self.clean_quotation_marks(name)
        
        # Check if it's a scripture reference
        if re.match(r'^\d+\s+[A-Z]', name):
            return self.format_scripture_reference(name)
        
        # Check if it looks like a title (multiple capitals, or keywords)
        is_title = (
            name.isupper() or 
            re.search(r'\b(The|A|An|And|Or)\b', name) or
            ': ' in name or  # Subtitles
            name.count(' ') > 2 and sum(1 for c in name if c.isupper()) > 2
        )
        
        if is_title and not re.match(r'^[A-Z]\.\s', name):  # Not an abbreviation
            return self.format_title_case(name)
        
        # Regular name - fix abbreviations
        return self.format_abbreviations(name)
    
    def print_author(self, author: Author) -> None:
        """Pretty print author info"""
        print(f"\n{'='*80}")
        print(f"ID: {author.id}")
        print(f"Name: {author.name}")
        
        # Validate current name
        is_valid, pattern = NameValidator.validate(author.name)
        if is_valid:
            print(f"Status: ✓ Valid ({pattern})")
        else:
            print(f"Status: ✗ Invalid format")
            fixes = NameValidator.suggest_fixes(author.name)
            if fixes:
                print("Suggested fixes:")
                for fix in fixes:
                    print(f"  - {fix}")
        
        if author.birth_year or author.death_year:
            years = f"{author.birth_year or '?'}-{author.death_year or '?'}"
            print(f"Years: {years}")
        if author.profession:
            print(f"Profession: {author.profession}")
        if author.nationality:
            print(f"Nationality: {author.nationality}")
        print(f"Quotes: {len(author.quotes)}")
        if author.quotes:
            print(f"Sample quote: {author.quotes[0].text[:70]}...")
        print(f"{'='*80}")
    
    def author_exists(self, name: str) -> bool:
        """Check if author with this name already exists"""
        try:
            return self.db.authors.get_by_name(name) is not None
        except:
            return False
    
    def merge_authors(self, from_author: Author, to_author: Author) -> None:
        """Move all quotes from one author to another, then delete the from_author"""
        print(f"\nMerging {len(from_author.quotes)} quotes from '{from_author.name}' to '{to_author.name}'...")
        
        # Move quotes
        for quote in from_author.quotes[:]:  # Use slice to avoid modification during iteration
            quote.author = to_author
        
        self.db.commit()
        
        # Delete the old author
        old_id = from_author.id
        self.db.session.delete(from_author)
        self.db.commit()
        
        # Log the merge
        self.changelog.add('MERGED', old_id, from_author.name, to_author.name, merged_with=to_author.name)
        
        print(f"✓ Merge complete!")
    
    def process_author(self, author: Author) -> None:
        """Interactive processing for a single author"""
        is_garbage, issues = self.is_likely_garbage(author.name)
        
        if is_garbage:
            print(f"\n⚠ Issues detected: {', '.join(issues)}")
        
        self.print_author(author)
        
        # Show suggestion
        suggestion = self.suggest_format(author.name)
        if suggestion != author.name:
            print(f"\nSuggested format: {suggestion}")
        else:
            print(f"\nNo format changes suggested.")
        
        while True:
            print("\nOptions:")
            print("  [1] Keep as is")
            if suggestion != author.name:
                print("  [2] Accept suggestion")
            print("  [3] Manual edit")
            print("  [4] Add to whitelist (skip)")
            print("  [5] Add to blacklist")
            print("  [6] Delete author and all quotes")
            print("  [7] Skip this author")
            
            choice = input("\nChoose option: ").strip()
            
            if choice == '1':
                self.skipped.append(author.name)
                print("✓ Keeping as is")
                return
            
            elif choice == '2' and suggestion != author.name:
                self._apply_change(author, suggestion)
                return
            
            elif choice == '3':
                new_name = input("Enter correct author name: ").strip()
                if new_name:
                    self._apply_change(author, new_name)
                    return
                else:
                    print("Name cannot be empty")
            
            elif choice == '4':
                self.whitelist.add(author.name, "User approved during sanitization")
                print(f"✓ Added '{author.name}' to whitelist")
                self.skipped.append(author.name)
                return
            
            elif choice == '5':
                reason = input("Reason for blacklisting: ").strip()
                self.blacklist.add_exact(author.name, reason or "Garbage/spam author")
                print(f"✓ Added '{author.name}' to blacklist")
                
                delete = input("Delete this author and quotes? (yes/no): ").strip().lower()
                if delete == 'yes':
                    self.db.session.delete(author)
                    self.db.commit()
                    print(f"✓ Deleted")
                    self.changes_made.append(f"DELETED: {author.name}")
                return
            
            elif choice == '6':
                confirm = input(f"Delete '{author.name}' and its {len(author.quotes)} quotes? (yes/no): ").strip().lower()
                if confirm == 'yes':
                    self.db.session.delete(author)
                    self.db.commit()
                    print(f"✓ Deleted")
                    self.changes_made.append(f"DELETED: {author.name}")
                    self.changelog.add('DELETED', author.id, author.name, "")
                    return
                else:
                    print("Cancelled")
            
            elif choice == '7':
                self.skipped.append(author.name)
                print("✓ Skipped")
                return
            
            else:
                print("Invalid option")
    
    def _apply_change(self, author: Author, new_name: str) -> None:
        """Apply a name change, handling duplicates"""
        new_name = new_name.strip()
        
        if new_name == author.name:
            print("No change made")
            return
        
        # Check if new name already exists
        existing = self.db.authors.get_by_name(new_name)
        
        if existing and existing.id != author.id:
            print(f"\n⚠ Author '{new_name}' already exists!")
            print(f"  Existing author has {len(existing.quotes)} quotes")
            print(f"  Current author '{author.name}' has {len(author.quotes)} quotes")
            
            merge_choice = input("\nMerge these authors? (yes/no): ").strip().lower()
            if merge_choice == 'yes':
                self.merge_authors(author, existing)
                self.changes_made.append(f"MERGED: '{author.name}' -> '{new_name}'")
            else:
                print("Cancelled - no changes made")
            return
        
        # Safe to rename
        old_name = author.name
        author.name = new_name
        author.unmark_for_edit()  # Remove the edit flag
        self.db.commit()
        
        # Log change
        self.changelog.add('RENAMED', author.id, old_name, new_name)
        
        print(f"✓ Changed: '{old_name}' -> '{new_name}'")
        self.changes_made.append(f"RENAMED: '{old_name}' -> '{new_name}'")
    
    def undo_last_change(self):
        """Undo the most recent change"""
        recent = self.changelog.get_latest(1)
        if not recent:
            print("No changes to undo")
            return
        
        change = recent[0]
        print(f"\nUndoing: {change}")
        print("Note: Undo is not yet implemented in the database layer")
        print("You would need to manually revert this change or restore from backup")
    
    def run_interactive(self):
        """Main interactive loop"""
        authors = self.needs_editing()
        
        if not authors:
            print("✓ No authors need editing!")
            return
        
        print(f"\nFound {len(authors)} authors needing editing")
        print("="*80)
        
        for i, author in enumerate(authors, 1):
            print(f"\n[{i}/{len(authors)}]")
            self.process_author(author)
        
        self.print_summary()
    
    def run_batch(self, auto_fix=False):
        """
        Run in batch mode - optionally auto-fix obvious issues
        
        Args:
            auto_fix: If True, automatically apply suggestions without confirmation
        """
        authors = self.needs_editing()
        
        if not authors:
            print("✓ No authors need editing!")
            return
        
        print(f"\nProcessing {len(authors)} authors...")
        print("="*80)
        
        for i, author in enumerate(authors, 1):
            is_garbage, issues = self.is_likely_garbage(author.name)
            suggestion = self.suggest_format(author.name)
            
            if suggestion != author.name:
                if auto_fix:
                    print(f"[{i}/{len(authors)}] Auto-fixing: {author.name}")
                    if not self.author_exists(suggestion):
                        self._apply_change(author, suggestion)
                    else:
                        existing = self.db.authors.get_by_name(suggestion)
                        self.merge_authors(author, existing)
                else:
                    print(f"[{i}/{len(authors)}] Review needed: {author.name}")
        
        self.print_summary()
    
    def print_summary(self):
        """Print summary of changes"""
        print(f"\n{'='*80}")
        print("SUMMARY")
        print(f"{'='*80}")
        print(f"Session started: {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Changes made: {len(self.changes_made)}")
        for change in self.changes_made:
            print(f"  ✓ {change}")
        
        if self.skipped:
            print(f"\nSkipped: {len(self.skipped)}")
            for name in self.skipped[:5]:
                print(f"  - {name}")
            if len(self.skipped) > 5:
                print(f"  ... and {len(self.skipped) - 5} more")
        
        # Export options
        print("\nExport options:")
        export_choice = input("Export changelog? (yes/no): ").strip().lower()
        if export_choice == 'yes':
            self.changelog.export()
        
        export_choice = input("Export whitelist? (yes/no): ").strip().lower()
        if export_choice == 'yes':
            self.whitelist.export()
        
        export_choice = input("Export blacklist? (yes/no): ").strip().lower()
        if export_choice == 'yes':
            self.blacklist.export()


def main():
    """Main entry point"""
    print("Author Name Sanitizer")
    print("="*80)
    
    sanitizer = AuthorSanitizer()
    
    try:
        while True:
            print("\nModes:")
            print("  [1] Interactive mode (review each author)")
            print("  [2] Batch mode (auto-fix obvious issues)")
            print("  [3] View recent changes")
            print("  [4] Manage whitelist")
            print("  [5] Manage blacklist")
            print("  [6] Exit")
            
            choice = input("\nChoose mode: ").strip()
            
            if choice == '1':
                sanitizer.run_interactive()
                break
            
            elif choice == '2':
                confirm = input("Auto-fix obvious issues? (yes/no): ").strip().lower()
                if confirm == 'yes':
                    sanitizer.run_batch(auto_fix=True)
                    break
                else:
                    print("Cancelled")
            
            elif choice == '3':
                recent = sanitizer.changelog.get_latest(10)
                print(f"\nRecent changes ({len(recent)} shown):")
                for change in recent:
                    print(f"  {change['timestamp']}: {change['type']} - {change['old_name']} -> {change['new_name']}")
            
            elif choice == '4':
                print("\nWhitelist Management:")
                print("  [1] View whitelist")
                print("  [2] Add to whitelist")
                print("  [3] Remove from whitelist")
                print("  [4] Back")
                sub_choice = input("Choose: ").strip()
                
                if sub_choice == '1':
                    if sanitizer.whitelist.names:
                        for name in sorted(list(sanitizer.whitelist.names))[:20]:
                            print(f"  - {name}")
                        if len(sanitizer.whitelist.names) > 20:
                            print(f"  ... and {len(sanitizer.whitelist.names) - 20} more")
                    else:
                        print("  Whitelist is empty")
                
                elif sub_choice == '2':
                    name = input("Enter author name: ").strip()
                    notes = input("Notes (optional): ").strip()
                    sanitizer.whitelist.add(name, notes)
                    print(f"✓ Added '{name}' to whitelist")
                
                elif sub_choice == '3':
                    name = input("Enter author name to remove: ").strip()
                    sanitizer.whitelist.remove(name)
                    print(f"✓ Removed '{name}' from whitelist")
            
            elif choice == '5':
                print("\nBlacklist Management:")
                print("  [1] View blacklist")
                print("  [2] Add exact name")
                print("  [3] Add pattern")
                print("  [4] Back")
                sub_choice = input("Choose: ").strip()
                
                if sub_choice == '1':
                    if sanitizer.blacklist.exact_names:
                        print("Exact names:")
                        for name in sorted(list(sanitizer.blacklist.exact_names))[:10]:
                            print(f"  - {name}")
                    if sanitizer.blacklist.patterns:
                        print("Patterns:")
                        for item in sanitizer.blacklist.patterns[:5]:
                            print(f"  - {item['pattern']} ({item.get('reason', 'N/A')})")
                
                elif sub_choice == '2':
                    name = input("Enter author name: ").strip()
                    reason = input("Reason: ").strip()
                    sanitizer.blacklist.add_exact(name, reason)
                    print(f"✓ Added '{name}' to blacklist")
                
                elif sub_choice == '3':
                    pattern = input("Enter regex pattern: ").strip()
                    reason = input("Reason: ").strip()
                    sanitizer.blacklist.add_pattern(pattern, reason)
                    print(f"✓ Added pattern to blacklist")
            
            elif choice == '6':
                print("Exiting...")
                break
            
            else:
                print("Invalid option")
    
    finally:
        sanitizer.close()


if __name__ == "__main__":
    main(),  # John M. Gottman
        'full_name': r'^[A-Z][a-z]+(\s+[A-Z][a-z]+)+(\s*\([^)]+\))?
    
    @staticmethod
    def validate(name: str) -> tuple[bool, str]:
        """
        Validate if a name matches expected format
        
        Returns:
            (is_valid, pattern_matched)
        """
        for pattern_name, pattern in NameValidator.PATTERNS.items():
            if re.match(pattern, name):
                return True, pattern_name
        
        return False, "unknown"
    
    @staticmethod
    def suggest_fixes(name: str) -> list[str]:
        """Suggest what might be wrong with a name"""
        fixes = []
        
        if name != name.strip():
            fixes.append("Remove leading/trailing whitespace")
        
        if '  ' in name:
            fixes.append("Remove extra spaces")
        
        if re.search(r'[a-z]\. [A-Z]', name):
            fixes.append("Lowercase letters should not precede periods in abbreviations")
        
        if re.search(r'([A-Z][a-z]*){3,}', name) and not re.search(r'\s', name):
            fixes.append("Name is missing spaces between parts")
        
        if name.isupper() and len(name) > 1:
            fixes.append("Name is all uppercase - should be title case")
        
        return fixes


class NameWhitelist:
    """Manage known good author names"""
    
    def __init__(self, whitelist_file: str = "author_whitelist.json"):
        self.whitelist_file = Path(whitelist_file)
        self.names = set()
        self.metadata = {}
        self.load()
    
    def load(self):
        """Load whitelist from disk"""
        if self.whitelist_file.exists():
            try:
                with open(self.whitelist_file, 'r') as f:
                    data = json.load(f)
                    self.names = set(data.get('names', []))
                    self.metadata = data.get('metadata', {})
            except:
                self.names = set()
                self.metadata = {}
    
    def save(self):
        """Save whitelist to disk"""
        with open(self.whitelist_file, 'w') as f:
            json.dump({
                'names': sorted(list(self.names)),
                'metadata': self.metadata,
                'count': len(self.names),
                'last_updated': datetime.now().isoformat()
            }, f, indent=2)
    
    def add(self, name: str, notes: str = ""):
        """Add a name to the whitelist"""
        self.names.add(name)
        if notes:
            self.metadata[name] = {'added': datetime.now().isoformat(), 'notes': notes}
        self.save()
    
    def remove(self, name: str):
        """Remove a name from whitelist"""
        self.names.discard(name)
        if name in self.metadata:
            del self.metadata[name]
        self.save()
    
    def is_whitelisted(self, name: str) -> bool:
        """Check if name is whitelisted"""
        return name in self.names
    
    def export(self, filename: str = "author_whitelist_export.json"):
        """Export whitelist"""
        with open(filename, 'w') as f:
            json.dump({
                'names': sorted(list(self.names)),
                'metadata': self.metadata,
                'count': len(self.names),
                'exported': datetime.now().isoformat()
            }, f, indent=2)
        print(f"✓ Exported {len(self.names)} whitelisted names to {filename}")


class NameBlacklist:
    """Manage known bad author name patterns"""
    
    def __init__(self, blacklist_file: str = "author_blacklist.json"):
        self.blacklist_file = Path(blacklist_file)
        self.patterns = []  # List of regex patterns
        self.exact_names = set()
        self.load()
    
    def load(self):
        """Load blacklist from disk"""
        if self.blacklist_file.exists():
            try:
                with open(self.blacklist_file, 'r') as f:
                    data = json.load(f)
                    self.patterns = data.get('patterns', [])
                    self.exact_names = set(data.get('exact_names', []))
            except:
                self.patterns = []
                self.exact_names = set()
    
    def save(self):
        """Save blacklist to disk"""
        with open(self.blacklist_file, 'w') as f:
            json.dump({
                'patterns': self.patterns,
                'exact_names': sorted(list(self.exact_names)),
                'total_patterns': len(self.patterns),
                'total_names': len(self.exact_names),
                'last_updated': datetime.now().isoformat()
            }, f, indent=2)
    
    def add_pattern(self, pattern: str, reason: str = ""):
        """Add a regex pattern to blacklist"""
        self.patterns.append({'pattern': pattern, 'reason': reason})
        self.save()
    
    def add_exact(self, name: str, reason: str = ""):
        """Add an exact name to blacklist"""
        self.exact_names.add(name)
        self.save()
    
    def is_blacklisted(self, name: str) -> tuple[bool, str]:
        """
        Check if name matches blacklist
        
        Returns:
            (is_blacklisted, reason)
        """
        # Check exact matches
        if name in self.exact_names:
            return True, "exact match in blacklist"
        
        # Check patterns
        for item in self.patterns:
            try:
                if re.search(item['pattern'], name):
                    return True, item.get('reason', 'matched pattern')
            except:
                pass
        
        return False, ""
    
    def export(self, filename: str = "author_blacklist_export.json"):
        """Export blacklist"""
        with open(filename, 'w') as f:
            json.dump({
                'patterns': self.patterns,
                'exact_names': sorted(list(self.exact_names)),
                'total_patterns': len(self.patterns),
                'total_names': len(self.exact_names),
                'exported': datetime.now().isoformat()
            }, f, indent=2)
        print(f"✓ Exported blacklist to {filename}")


class AuthorSanitizer:
    """Interactive tool for cleaning and standardizing author names"""
    
    def __init__(self):
        self.db = DB()
        self.changelog = ChangeLog()
        self.whitelist = NameWhitelist()
        self.blacklist = NameBlacklist()
        self.changes_made = []
        self.skipped = []
        self.session_start = datetime.now()
    
    def close(self):
        """Close database connection"""
        self.db.close()
    
    def needs_editing(self):
        """Get all authors marked for editing"""
        return self.db.authors.needs_edit()
    
    def is_likely_garbage(self, name: str) -> tuple[bool, list[str]]:
        """Check if author name looks suspicious/needs attention"""
        issues = []
        
        # Check blacklist first
        is_blacklisted, reason = self.blacklist.is_blacklisted(name)
        if is_blacklisted:
            issues.append(f"blacklist match ({reason})")
        
        # Check whitelist
        if self.whitelist.is_whitelisted(name):
            return False, []  # Whitelisted = good to go
        
        # Check for excessive quotation marks
        if name.count('"') > 2:
            issues.append(f"excessive quotes ({name.count('\"')} found)")
        
        # Check for malformed abbreviations (C.S.Lewis instead of C. S. Lewis)
        if re.search(r'[A-Z]\.[A-Z]\.', name) and not re.search(r'[A-Z]\. [A-Z]\.', name):
            issues.append("improper abbreviation spacing")
        
        # Check for mixed case that suggests garbage
        if re.search(r'[A-Z][a-z]*[A-Z]', name) and not re.search(r'\(', name):
            issues.append("unusual capitalization")
        
        # Check for numbers at start (scripture references)
        if re.match(r'^\d+', name) and not re.match(r'^\d+\s+[A-Za-z]+', name):
            issues.append("possible malformed scripture reference")
        
        # Check for excessive punctuation
        if name.count('.') > 4:
            issues.append("excessive periods")
        
        # Check format validity
        is_valid, pattern = NameValidator.validate(name)
        if not is_valid:
            issues.append(f"doesn't match standard patterns")
        
        return len(issues) > 0, issues
    
    def clean_quotation_marks(self, name: str) -> str:
        """Remove excessive embedded quotation marks, extracting the content"""
        # Pattern: text """""content""""" text -> text (content) text
        match = re.search(r'(\w+)\s+"{2,}(.+?)"{2,}\s+(\w+)', name)
        if match:
            before = match.group(1)
            content = match.group(2).strip()
            after = match.group(3)
            return f"{before} {after} ({content})"
        
        # Just remove quotes if no clear pattern
        return name.replace('"', '')
    
    def format_abbreviations(self, name: str) -> str:
        """Fix abbreviation spacing: C.S. Lewis -> C. S. Lewis"""
        # Find patterns like C.S. and fix to C. S.
        name = re.sub(r'([A-Z])\.([A-Z])\.', r'\1. \2.', name)
        # Fix spacing after abbreviations if needed
        name = re.sub(r'([A-Z]\.) ([A-Z]\.)', r'\1 \2', name)
        return name.strip()
    
    def format_title_case(self, name: str) -> str:
        """Convert to title case, respecting articles and prepositions"""
        # Words that should be lowercase in titles (unless first word)
        lowercase_words = {'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        
        # Preserve parenthetical content
        paren_match = re.match(r'^(.*?)(\(.+\))$', name)
        if paren_match:
            title = paren_match.group(1).strip()
            paren = paren_match.group(2)
            name = title
            preserve_paren = paren
        else:
            preserve_paren = None
        
        # Split and process words
        words = name.split()
        result = []
        
        for i, word in enumerate(words):
            if i == 0 or word.lower() not in lowercase_words:
                result.append(word.capitalize())
            else:
                result.append(word.lower())
        
        final = ' '.join(result)
        if preserve_paren:
            final = f"{final} {preserve_paren}"
        
        return final
    
    def format_scripture_reference(self, name: str) -> str:
        """Format scripture references: 1 Kings 1:12-14 or 1 Kings 1 (NIV)"""
        # Already well-formatted
        if re.match(r'^\d+\s+[A-Za-z]+\s+\d+', name):
            return name
        return name
    
    def suggest_format(self, name: str) -> str:
        """Suggest how the name should be formatted"""
        original = name
        
        # Clean garbage quotation marks first
        if '"""' in name or '""""' in name:
            name = self.clean_quotation_marks(name)
        
        # Check if it's a scripture reference
        if re.match(r'^\d+\s+[A-Z]', name):
            return self.format_scripture_reference(name)
        
        # Check if it looks like a title (multiple capitals, or keywords)
        is_title = (
            name.isupper() or 
            re.search(r'\b(The|A|An|And|Or)\b', name) or
            ': ' in name or  # Subtitles
            name.count(' ') > 2 and sum(1 for c in name if c.isupper()) > 2
        )
        
        if is_title and not re.match(r'^[A-Z]\.\s', name):  # Not an abbreviation
            return self.format_title_case(name)
        
        # Regular name - fix abbreviations
        return self.format_abbreviations(name)
    
    def print_author(self, author: Author) -> None:
        """Pretty print author info"""
        print(f"\n{'='*80}")
        print(f"ID: {author.id}")
        print(f"Name: {author.name}")
        
        # Validate current name
        is_valid, pattern = NameValidator.validate(author.name)
        if is_valid:
            print(f"Status: ✓ Valid ({pattern})")
        else:
            print(f"Status: ✗ Invalid format")
            fixes = NameValidator.suggest_fixes(author.name)
            if fixes:
                print("Suggested fixes:")
                for fix in fixes:
                    print(f"  - {fix}")
        
        if author.birth_year or author.death_year:
            years = f"{author.birth_year or '?'}-{author.death_year or '?'}"
            print(f"Years: {years}")
        if author.profession:
            print(f"Profession: {author.profession}")
        if author.nationality:
            print(f"Nationality: {author.nationality}")
        print(f"Quotes: {len(author.quotes)}")
        if author.quotes:
            print(f"Sample quote: {author.quotes[0].text[:70]}...")
        print(f"{'='*80}")
    
    def author_exists(self, name: str) -> bool:
        """Check if author with this name already exists"""
        try:
            return self.db.authors.get_by_name(name) is not None
        except:
            return False
    
    def merge_authors(self, from_author: Author, to_author: Author) -> None:
        """Move all quotes from one author to another, then delete the from_author"""
        print(f"\nMerging {len(from_author.quotes)} quotes from '{from_author.name}' to '{to_author.name}'...")
        
        # Move quotes
        for quote in from_author.quotes[:]:  # Use slice to avoid modification during iteration
            quote.author = to_author
        
        self.db.commit()
        
        # Delete the old author
        old_id = from_author.id
        self.db.session.delete(from_author)
        self.db.commit()
        
        # Log the merge
        self.changelog.add('MERGED', old_id, from_author.name, to_author.name, merged_with=to_author.name)
        
        print(f"✓ Merge complete!")
    
    def process_author(self, author: Author) -> None:
        """Interactive processing for a single author"""
        is_garbage, issues = self.is_likely_garbage(author.name)
        
        if is_garbage:
            print(f"\n⚠ Issues detected: {', '.join(issues)}")
        
        self.print_author(author)
        
        # Show suggestion
        suggestion = self.suggest_format(author.name)
        if suggestion != author.name:
            print(f"\nSuggested format: {suggestion}")
        else:
            print(f"\nNo format changes suggested.")
        
        while True:
            print("\nOptions:")
            print("  [1] Keep as is")
            if suggestion != author.name:
                print("  [2] Accept suggestion")
            print("  [3] Manual edit")
            print("  [4] Add to whitelist (skip)")
            print("  [5] Add to blacklist")
            print("  [6] Delete author and all quotes")
            print("  [7] Skip this author")
            
            choice = input("\nChoose option: ").strip()
            
            if choice == '1':
                self.skipped.append(author.name)
                print("✓ Keeping as is")
                return
            
            elif choice == '2' and suggestion != author.name:
                self._apply_change(author, suggestion)
                return
            
            elif choice == '3':
                new_name = input("Enter correct author name: ").strip()
                if new_name:
                    self._apply_change(author, new_name)
                    return
                else:
                    print("Name cannot be empty")
            
            elif choice == '4':
                self.whitelist.add(author.name, "User approved during sanitization")
                print(f"✓ Added '{author.name}' to whitelist")
                self.skipped.append(author.name)
                return
            
            elif choice == '5':
                reason = input("Reason for blacklisting: ").strip()
                self.blacklist.add_exact(author.name, reason or "Garbage/spam author")
                print(f"✓ Added '{author.name}' to blacklist")
                
                delete = input("Delete this author and quotes? (yes/no): ").strip().lower()
                if delete == 'yes':
                    self.db.session.delete(author)
                    self.db.commit()
                    print(f"✓ Deleted")
                    self.changes_made.append(f"DELETED: {author.name}")
                return
            
            elif choice == '6':
                confirm = input(f"Delete '{author.name}' and its {len(author.quotes)} quotes? (yes/no): ").strip().lower()
                if confirm == 'yes':
                    self.db.session.delete(author)
                    self.db.commit()
                    print(f"✓ Deleted")
                    self.changes_made.append(f"DELETED: {author.name}")
                    self.changelog.add('DELETED', author.id, author.name, "")
                    return
                else:
                    print("Cancelled")
            
            elif choice == '7':
                self.skipped.append(author.name)
                print("✓ Skipped")
                return
            
            else:
                print("Invalid option")
    
    def _apply_change(self, author: Author, new_name: str) -> None:
        """Apply a name change, handling duplicates"""
        new_name = new_name.strip()
        
        if new_name == author.name:
            print("No change made")
            return
        
        # Check if new name already exists
        existing = self.db.authors.get_by_name(new_name)
        
        if existing and existing.id != author.id:
            print(f"\n⚠ Author '{new_name}' already exists!")
            print(f"  Existing author has {len(existing.quotes)} quotes")
            print(f"  Current author '{author.name}' has {len(author.quotes)} quotes")
            
            merge_choice = input("\nMerge these authors? (yes/no): ").strip().lower()
            if merge_choice == 'yes':
                self.merge_authors(author, existing)
                self.changes_made.append(f"MERGED: '{author.name}' -> '{new_name}'")
            else:
                print("Cancelled - no changes made")
            return
        
        # Safe to rename
        old_name = author.name
        author.name = new_name
        author.unmark_for_edit()  # Remove the edit flag
        self.db.commit()
        
        # Log change
        self.changelog.add('RENAMED', author.id, old_name, new_name)
        
        print(f"✓ Changed: '{old_name}' -> '{new_name}'")
        self.changes_made.append(f"RENAMED: '{old_name}' -> '{new_name}'")
    
    def undo_last_change(self):
        """Undo the most recent change"""
        recent = self.changelog.get_latest(1)
        if not recent:
            print("No changes to undo")
            return
        
        change = recent[0]
        print(f"\nUndoing: {change}")
        print("Note: Undo is not yet implemented in the database layer")
        print("You would need to manually revert this change or restore from backup")
    
    def run_interactive(self):
        """Main interactive loop"""
        authors = self.needs_editing()
        
        if not authors:
            print("✓ No authors need editing!")
            return
        
        print(f"\nFound {len(authors)} authors needing editing")
        print("="*80)
        
        for i, author in enumerate(authors, 1):
            print(f"\n[{i}/{len(authors)}]")
            self.process_author(author)
        
        self.print_summary()
    
    def run_batch(self, auto_fix=False):
        """
        Run in batch mode - optionally auto-fix obvious issues
        
        Args:
            auto_fix: If True, automatically apply suggestions without confirmation
        """
        authors = self.needs_editing()
        
        if not authors:
            print("✓ No authors need editing!")
            return
        
        print(f"\nProcessing {len(authors)} authors...")
        print("="*80)
        
        for i, author in enumerate(authors, 1):
            is_garbage, issues = self.is_likely_garbage(author.name)
            suggestion = self.suggest_format(author.name)
            
            if suggestion != author.name:
                if auto_fix:
                    print(f"[{i}/{len(authors)}] Auto-fixing: {author.name}")
                    if not self.author_exists(suggestion):
                        self._apply_change(author, suggestion)
                    else:
                        existing = self.db.authors.get_by_name(suggestion)
                        self.merge_authors(author, existing)
                else:
                    print(f"[{i}/{len(authors)}] Review needed: {author.name}")
        
        self.print_summary()
    
    def print_summary(self):
        """Print summary of changes"""
        print(f"\n{'='*80}")
        print("SUMMARY")
        print(f"{'='*80}")
        print(f"Session started: {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Changes made: {len(self.changes_made)}")
        for change in self.changes_made:
            print(f"  ✓ {change}")
        
        if self.skipped:
            print(f"\nSkipped: {len(self.skipped)}")
            for name in self.skipped[:5]:
                print(f"  - {name}")
            if len(self.skipped) > 5:
                print(f"  ... and {len(self.skipped) - 5} more")
        
        # Export options
        print("\nExport options:")
        export_choice = input("Export changelog? (yes/no): ").strip().lower()
        if export_choice == 'yes':
            self.changelog.export()
        
        export_choice = input("Export whitelist? (yes/no): ").strip().lower()
        if export_choice == 'yes':
            self.whitelist.export()
        
        export_choice = input("Export blacklist? (yes/no): ").strip().lower()
        if export_choice == 'yes':
            self.blacklist.export()


def main():
    """Main entry point"""
    print("Author Name Sanitizer")
    print("="*80)
    
    sanitizer = AuthorSanitizer()
    
    try:
        while True:
            print("\nModes:")
            print("  [1] Interactive mode (review each author)")
            print("  [2] Batch mode (auto-fix obvious issues)")
            print("  [3] View recent changes")
            print("  [4] Manage whitelist")
            print("  [5] Manage blacklist")
            print("  [6] Exit")
            
            choice = input("\nChoose mode: ").strip()
            
            if choice == '1':
                sanitizer.run_interactive()
                break
            
            elif choice == '2':
                confirm = input("Auto-fix obvious issues? (yes/no): ").strip().lower()
                if confirm == 'yes':
                    sanitizer.run_batch(auto_fix=True)
                    break
                else:
                    print("Cancelled")
            
            elif choice == '3':
                recent = sanitizer.changelog.get_latest(10)
                print(f"\nRecent changes ({len(recent)} shown):")
                for change in recent:
                    print(f"  {change['timestamp']}: {change['type']} - {change['old_name']} -> {change['new_name']}")
            
            elif choice == '4':
                print("\nWhitelist Management:")
                print("  [1] View whitelist")
                print("  [2] Add to whitelist")
                print("  [3] Remove from whitelist")
                print("  [4] Back")
                sub_choice = input("Choose: ").strip()
                
                if sub_choice == '1':
                    if sanitizer.whitelist.names:
                        for name in sorted(list(sanitizer.whitelist.names))[:20]:
                            print(f"  - {name}")
                        if len(sanitizer.whitelist.names) > 20:
                            print(f"  ... and {len(sanitizer.whitelist.names) - 20} more")
                    else:
                        print("  Whitelist is empty")
                
                elif sub_choice == '2':
                    name = input("Enter author name: ").strip()
                    notes = input("Notes (optional): ").strip()
                    sanitizer.whitelist.add(name, notes)
                    print(f"✓ Added '{name}' to whitelist")
                
                elif sub_choice == '3':
                    name = input("Enter author name to remove: ").strip()
                    sanitizer.whitelist.remove(name)
                    print(f"✓ Removed '{name}' from whitelist")
            
            elif choice == '5':
                print("\nBlacklist Management:")
                print("  [1] View blacklist")
                print("  [2] Add exact name")
                print("  [3] Add pattern")
                print("  [4] Back")
                sub_choice = input("Choose: ").strip()
                
                if sub_choice == '1':
                    if sanitizer.blacklist.exact_names:
                        print("Exact names:")
                        for name in sorted(list(sanitizer.blacklist.exact_names))[:10]:
                            print(f"  - {name}")
                    if sanitizer.blacklist.patterns:
                        print("Patterns:")
                        for item in sanitizer.blacklist.patterns[:5]:
                            print(f"  - {item['pattern']} ({item.get('reason', 'N/A')})")
                
                elif sub_choice == '2':
                    name = input("Enter author name: ").strip()
                    reason = input("Reason: ").strip()
                    sanitizer.blacklist.add_exact(name, reason)
                    print(f"✓ Added '{name}' to blacklist")
                
                elif sub_choice == '3':
                    pattern = input("Enter regex pattern: ").strip()
                    reason = input("Reason: ").strip()
                    sanitizer.blacklist.add_pattern(pattern, reason)
                    print(f"✓ Added pattern to blacklist")
            
            elif choice == '6':
                print("Exiting...")
                break
            
            else:
                print("Invalid option")
    
    finally:
        sanitizer.close()


if __name__ == "__main__":
    main(),  # John Michael Gottman
        'title': r'^[A-Z][a-z]+(\s+(And|The|A|An|Or|In|Of|With|By)[a-z]+)*(\s*\([^)]+\))?
    
    @staticmethod
    def validate(name: str) -> tuple[bool, str]:
        """
        Validate if a name matches expected format
        
        Returns:
            (is_valid, pattern_matched)
        """
        for pattern_name, pattern in NameValidator.PATTERNS.items():
            if re.match(pattern, name):
                return True, pattern_name
        
        return False, "unknown"
    
    @staticmethod
    def suggest_fixes(name: str) -> list[str]:
        """Suggest what might be wrong with a name"""
        fixes = []
        
        if name != name.strip():
            fixes.append("Remove leading/trailing whitespace")
        
        if '  ' in name:
            fixes.append("Remove extra spaces")
        
        if re.search(r'[a-z]\. [A-Z]', name):
            fixes.append("Lowercase letters should not precede periods in abbreviations")
        
        if re.search(r'([A-Z][a-z]*){3,}', name) and not re.search(r'\s', name):
            fixes.append("Name is missing spaces between parts")
        
        if name.isupper() and len(name) > 1:
            fixes.append("Name is all uppercase - should be title case")
        
        return fixes


class NameWhitelist:
    """Manage known good author names"""
    
    def __init__(self, whitelist_file: str = "author_whitelist.json"):
        self.whitelist_file = Path(whitelist_file)
        self.names = set()
        self.metadata = {}
        self.load()
    
    def load(self):
        """Load whitelist from disk"""
        if self.whitelist_file.exists():
            try:
                with open(self.whitelist_file, 'r') as f:
                    data = json.load(f)
                    self.names = set(data.get('names', []))
                    self.metadata = data.get('metadata', {})
            except:
                self.names = set()
                self.metadata = {}
    
    def save(self):
        """Save whitelist to disk"""
        with open(self.whitelist_file, 'w') as f:
            json.dump({
                'names': sorted(list(self.names)),
                'metadata': self.metadata,
                'count': len(self.names),
                'last_updated': datetime.now().isoformat()
            }, f, indent=2)
    
    def add(self, name: str, notes: str = ""):
        """Add a name to the whitelist"""
        self.names.add(name)
        if notes:
            self.metadata[name] = {'added': datetime.now().isoformat(), 'notes': notes}
        self.save()
    
    def remove(self, name: str):
        """Remove a name from whitelist"""
        self.names.discard(name)
        if name in self.metadata:
            del self.metadata[name]
        self.save()
    
    def is_whitelisted(self, name: str) -> bool:
        """Check if name is whitelisted"""
        return name in self.names
    
    def export(self, filename: str = "author_whitelist_export.json"):
        """Export whitelist"""
        with open(filename, 'w') as f:
            json.dump({
                'names': sorted(list(self.names)),
                'metadata': self.metadata,
                'count': len(self.names),
                'exported': datetime.now().isoformat()
            }, f, indent=2)
        print(f"✓ Exported {len(self.names)} whitelisted names to {filename}")


class NameBlacklist:
    """Manage known bad author name patterns"""
    
    def __init__(self, blacklist_file: str = "author_blacklist.json"):
        self.blacklist_file = Path(blacklist_file)
        self.patterns = []  # List of regex patterns
        self.exact_names = set()
        self.load()
    
    def load(self):
        """Load blacklist from disk"""
        if self.blacklist_file.exists():
            try:
                with open(self.blacklist_file, 'r') as f:
                    data = json.load(f)
                    self.patterns = data.get('patterns', [])
                    self.exact_names = set(data.get('exact_names', []))
            except:
                self.patterns = []
                self.exact_names = set()
    
    def save(self):
        """Save blacklist to disk"""
        with open(self.blacklist_file, 'w') as f:
            json.dump({
                'patterns': self.patterns,
                'exact_names': sorted(list(self.exact_names)),
                'total_patterns': len(self.patterns),
                'total_names': len(self.exact_names),
                'last_updated': datetime.now().isoformat()
            }, f, indent=2)
    
    def add_pattern(self, pattern: str, reason: str = ""):
        """Add a regex pattern to blacklist"""
        self.patterns.append({'pattern': pattern, 'reason': reason})
        self.save()
    
    def add_exact(self, name: str, reason: str = ""):
        """Add an exact name to blacklist"""
        self.exact_names.add(name)
        self.save()
    
    def is_blacklisted(self, name: str) -> tuple[bool, str]:
        """
        Check if name matches blacklist
        
        Returns:
            (is_blacklisted, reason)
        """
        # Check exact matches
        if name in self.exact_names:
            return True, "exact match in blacklist"
        
        # Check patterns
        for item in self.patterns:
            try:
                if re.search(item['pattern'], name):
                    return True, item.get('reason', 'matched pattern')
            except:
                pass
        
        return False, ""
    
    def export(self, filename: str = "author_blacklist_export.json"):
        """Export blacklist"""
        with open(filename, 'w') as f:
            json.dump({
                'patterns': self.patterns,
                'exact_names': sorted(list(self.exact_names)),
                'total_patterns': len(self.patterns),
                'total_names': len(self.exact_names),
                'exported': datetime.now().isoformat()
            }, f, indent=2)
        print(f"✓ Exported blacklist to {filename}")


class AuthorSanitizer:
    """Interactive tool for cleaning and standardizing author names"""
    
    def __init__(self):
        self.db = DB()
        self.changelog = ChangeLog()
        self.whitelist = NameWhitelist()
        self.blacklist = NameBlacklist()
        self.changes_made = []
        self.skipped = []
        self.session_start = datetime.now()
    
    def close(self):
        """Close database connection"""
        self.db.close()
    
    def needs_editing(self):
        """Get all authors marked for editing"""
        return self.db.authors.needs_edit()
    
    def is_likely_garbage(self, name: str) -> tuple[bool, list[str]]:
        """Check if author name looks suspicious/needs attention"""
        issues = []
        
        # Check blacklist first
        is_blacklisted, reason = self.blacklist.is_blacklisted(name)
        if is_blacklisted:
            issues.append(f"blacklist match ({reason})")
        
        # Check whitelist
        if self.whitelist.is_whitelisted(name):
            return False, []  # Whitelisted = good to go
        
        # Check for excessive quotation marks
        if name.count('"') > 2:
            issues.append(f"excessive quotes ({name.count('\"')} found)")
        
        # Check for malformed abbreviations (C.S.Lewis instead of C. S. Lewis)
        if re.search(r'[A-Z]\.[A-Z]\.', name) and not re.search(r'[A-Z]\. [A-Z]\.', name):
            issues.append("improper abbreviation spacing")
        
        # Check for mixed case that suggests garbage
        if re.search(r'[A-Z][a-z]*[A-Z]', name) and not re.search(r'\(', name):
            issues.append("unusual capitalization")
        
        # Check for numbers at start (scripture references)
        if re.match(r'^\d+', name) and not re.match(r'^\d+\s+[A-Za-z]+', name):
            issues.append("possible malformed scripture reference")
        
        # Check for excessive punctuation
        if name.count('.') > 4:
            issues.append("excessive periods")
        
        # Check format validity
        is_valid, pattern = NameValidator.validate(name)
        if not is_valid:
            issues.append(f"doesn't match standard patterns")
        
        return len(issues) > 0, issues
    
    def clean_quotation_marks(self, name: str) -> str:
        """Remove excessive embedded quotation marks, extracting the content"""
        # Pattern: text """""content""""" text -> text (content) text
        match = re.search(r'(\w+)\s+"{2,}(.+?)"{2,}\s+(\w+)', name)
        if match:
            before = match.group(1)
            content = match.group(2).strip()
            after = match.group(3)
            return f"{before} {after} ({content})"
        
        # Just remove quotes if no clear pattern
        return name.replace('"', '')
    
    def format_abbreviations(self, name: str) -> str:
        """Fix abbreviation spacing: C.S. Lewis -> C. S. Lewis"""
        # Find patterns like C.S. and fix to C. S.
        name = re.sub(r'([A-Z])\.([A-Z])\.', r'\1. \2.', name)
        # Fix spacing after abbreviations if needed
        name = re.sub(r'([A-Z]\.) ([A-Z]\.)', r'\1 \2', name)
        return name.strip()
    
    def format_title_case(self, name: str) -> str:
        """Convert to title case, respecting articles and prepositions"""
        # Words that should be lowercase in titles (unless first word)
        lowercase_words = {'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        
        # Preserve parenthetical content
        paren_match = re.match(r'^(.*?)(\(.+\))$', name)
        if paren_match:
            title = paren_match.group(1).strip()
            paren = paren_match.group(2)
            name = title
            preserve_paren = paren
        else:
            preserve_paren = None
        
        # Split and process words
        words = name.split()
        result = []
        
        for i, word in enumerate(words):
            if i == 0 or word.lower() not in lowercase_words:
                result.append(word.capitalize())
            else:
                result.append(word.lower())
        
        final = ' '.join(result)
        if preserve_paren:
            final = f"{final} {preserve_paren}"
        
        return final
    
    def format_scripture_reference(self, name: str) -> str:
        """Format scripture references: 1 Kings 1:12-14 or 1 Kings 1 (NIV)"""
        # Already well-formatted
        if re.match(r'^\d+\s+[A-Za-z]+\s+\d+', name):
            return name
        return name
    
    def suggest_format(self, name: str) -> str:
        """Suggest how the name should be formatted"""
        original = name
        
        # Clean garbage quotation marks first
        if '"""' in name or '""""' in name:
            name = self.clean_quotation_marks(name)
        
        # Check if it's a scripture reference
        if re.match(r'^\d+\s+[A-Z]', name):
            return self.format_scripture_reference(name)
        
        # Check if it looks like a title (multiple capitals, or keywords)
        is_title = (
            name.isupper() or 
            re.search(r'\b(The|A|An|And|Or)\b', name) or
            ': ' in name or  # Subtitles
            name.count(' ') > 2 and sum(1 for c in name if c.isupper()) > 2
        )
        
        if is_title and not re.match(r'^[A-Z]\.\s', name):  # Not an abbreviation
            return self.format_title_case(name)
        
        # Regular name - fix abbreviations
        return self.format_abbreviations(name)
    
    def print_author(self, author: Author) -> None:
        """Pretty print author info"""
        print(f"\n{'='*80}")
        print(f"ID: {author.id}")
        print(f"Name: {author.name}")
        
        # Validate current name
        is_valid, pattern = NameValidator.validate(author.name)
        if is_valid:
            print(f"Status: ✓ Valid ({pattern})")
        else:
            print(f"Status: ✗ Invalid format")
            fixes = NameValidator.suggest_fixes(author.name)
            if fixes:
                print("Suggested fixes:")
                for fix in fixes:
                    print(f"  - {fix}")
        
        if author.birth_year or author.death_year:
            years = f"{author.birth_year or '?'}-{author.death_year or '?'}"
            print(f"Years: {years}")
        if author.profession:
            print(f"Profession: {author.profession}")
        if author.nationality:
            print(f"Nationality: {author.nationality}")
        print(f"Quotes: {len(author.quotes)}")
        if author.quotes:
            print(f"Sample quote: {author.quotes[0].text[:70]}...")
        print(f"{'='*80}")
    
    def author_exists(self, name: str) -> bool:
        """Check if author with this name already exists"""
        try:
            return self.db.authors.get_by_name(name) is not None
        except:
            return False
    
    def merge_authors(self, from_author: Author, to_author: Author) -> None:
        """Move all quotes from one author to another, then delete the from_author"""
        print(f"\nMerging {len(from_author.quotes)} quotes from '{from_author.name}' to '{to_author.name}'...")
        
        # Move quotes
        for quote in from_author.quotes[:]:  # Use slice to avoid modification during iteration
            quote.author = to_author
        
        self.db.commit()
        
        # Delete the old author
        old_id = from_author.id
        self.db.session.delete(from_author)
        self.db.commit()
        
        # Log the merge
        self.changelog.add('MERGED', old_id, from_author.name, to_author.name, merged_with=to_author.name)
        
        print(f"✓ Merge complete!")
    
    def process_author(self, author: Author) -> None:
        """Interactive processing for a single author"""
        is_garbage, issues = self.is_likely_garbage(author.name)
        
        if is_garbage:
            print(f"\n⚠ Issues detected: {', '.join(issues)}")
        
        self.print_author(author)
        
        # Show suggestion
        suggestion = self.suggest_format(author.name)
        if suggestion != author.name:
            print(f"\nSuggested format: {suggestion}")
        else:
            print(f"\nNo format changes suggested.")
        
        while True:
            print("\nOptions:")
            print("  [1] Keep as is")
            if suggestion != author.name:
                print("  [2] Accept suggestion")
            print("  [3] Manual edit")
            print("  [4] Add to whitelist (skip)")
            print("  [5] Add to blacklist")
            print("  [6] Delete author and all quotes")
            print("  [7] Skip this author")
            
            choice = input("\nChoose option: ").strip()
            
            if choice == '1':
                self.skipped.append(author.name)
                print("✓ Keeping as is")
                return
            
            elif choice == '2' and suggestion != author.name:
                self._apply_change(author, suggestion)
                return
            
            elif choice == '3':
                new_name = input("Enter correct author name: ").strip()
                if new_name:
                    self._apply_change(author, new_name)
                    return
                else:
                    print("Name cannot be empty")
            
            elif choice == '4':
                self.whitelist.add(author.name, "User approved during sanitization")
                print(f"✓ Added '{author.name}' to whitelist")
                self.skipped.append(author.name)
                return
            
            elif choice == '5':
                reason = input("Reason for blacklisting: ").strip()
                self.blacklist.add_exact(author.name, reason or "Garbage/spam author")
                print(f"✓ Added '{author.name}' to blacklist")
                
                delete = input("Delete this author and quotes? (yes/no): ").strip().lower()
                if delete == 'yes':
                    self.db.session.delete(author)
                    self.db.commit()
                    print(f"✓ Deleted")
                    self.changes_made.append(f"DELETED: {author.name}")
                return
            
            elif choice == '6':
                confirm = input(f"Delete '{author.name}' and its {len(author.quotes)} quotes? (yes/no): ").strip().lower()
                if confirm == 'yes':
                    self.db.session.delete(author)
                    self.db.commit()
                    print(f"✓ Deleted")
                    self.changes_made.append(f"DELETED: {author.name}")
                    self.changelog.add('DELETED', author.id, author.name, "")
                    return
                else:
                    print("Cancelled")
            
            elif choice == '7':
                self.skipped.append(author.name)
                print("✓ Skipped")
                return
            
            else:
                print("Invalid option")
    
    def _apply_change(self, author: Author, new_name: str) -> None:
        """Apply a name change, handling duplicates"""
        new_name = new_name.strip()
        
        if new_name == author.name:
            print("No change made")
            return
        
        # Check if new name already exists
        existing = self.db.authors.get_by_name(new_name)
        
        if existing and existing.id != author.id:
            print(f"\n⚠ Author '{new_name}' already exists!")
            print(f"  Existing author has {len(existing.quotes)} quotes")
            print(f"  Current author '{author.name}' has {len(author.quotes)} quotes")
            
            merge_choice = input("\nMerge these authors? (yes/no): ").strip().lower()
            if merge_choice == 'yes':
                self.merge_authors(author, existing)
                self.changes_made.append(f"MERGED: '{author.name}' -> '{new_name}'")
            else:
                print("Cancelled - no changes made")
            return
        
        # Safe to rename
        old_name = author.name
        author.name = new_name
        author.unmark_for_edit()  # Remove the edit flag
        self.db.commit()
        
        # Log change
        self.changelog.add('RENAMED', author.id, old_name, new_name)
        
        print(f"✓ Changed: '{old_name}' -> '{new_name}'")
        self.changes_made.append(f"RENAMED: '{old_name}' -> '{new_name}'")
    
    def undo_last_change(self):
        """Undo the most recent change"""
        recent = self.changelog.get_latest(1)
        if not recent:
            print("No changes to undo")
            return
        
        change = recent[0]
        print(f"\nUndoing: {change}")
        print("Note: Undo is not yet implemented in the database layer")
        print("You would need to manually revert this change or restore from backup")
    
    def run_interactive(self):
        """Main interactive loop"""
        authors = self.needs_editing()
        
        if not authors:
            print("✓ No authors need editing!")
            return
        
        print(f"\nFound {len(authors)} authors needing editing")
        print("="*80)
        
        for i, author in enumerate(authors, 1):
            print(f"\n[{i}/{len(authors)}]")
            self.process_author(author)
        
        self.print_summary()
    
    def run_batch(self, auto_fix=False):
        """
        Run in batch mode - optionally auto-fix obvious issues
        
        Args:
            auto_fix: If True, automatically apply suggestions without confirmation
        """
        authors = self.needs_editing()
        
        if not authors:
            print("✓ No authors need editing!")
            return
        
        print(f"\nProcessing {len(authors)} authors...")
        print("="*80)
        
        for i, author in enumerate(authors, 1):
            is_garbage, issues = self.is_likely_garbage(author.name)
            suggestion = self.suggest_format(author.name)
            
            if suggestion != author.name:
                if auto_fix:
                    print(f"[{i}/{len(authors)}] Auto-fixing: {author.name}")
                    if not self.author_exists(suggestion):
                        self._apply_change(author, suggestion)
                    else:
                        existing = self.db.authors.get_by_name(suggestion)
                        self.merge_authors(author, existing)
                else:
                    print(f"[{i}/{len(authors)}] Review needed: {author.name}")
        
        self.print_summary()
    
    def print_summary(self):
        """Print summary of changes"""
        print(f"\n{'='*80}")
        print("SUMMARY")
        print(f"{'='*80}")
        print(f"Session started: {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Changes made: {len(self.changes_made)}")
        for change in self.changes_made:
            print(f"  ✓ {change}")
        
        if self.skipped:
            print(f"\nSkipped: {len(self.skipped)}")
            for name in self.skipped[:5]:
                print(f"  - {name}")
            if len(self.skipped) > 5:
                print(f"  ... and {len(self.skipped) - 5} more")
        
        # Export options
        print("\nExport options:")
        export_choice = input("Export changelog? (yes/no): ").strip().lower()
        if export_choice == 'yes':
            self.changelog.export()
        
        export_choice = input("Export whitelist? (yes/no): ").strip().lower()
        if export_choice == 'yes':
            self.whitelist.export()
        
        export_choice = input("Export blacklist? (yes/no): ").strip().lower()
        if export_choice == 'yes':
            self.blacklist.export()


def main():
    """Main entry point"""
    print("Author Name Sanitizer")
    print("="*80)
    
    sanitizer = AuthorSanitizer()
    
    try:
        while True:
            print("\nModes:")
            print("  [1] Interactive mode (review each author)")
            print("  [2] Batch mode (auto-fix obvious issues)")
            print("  [3] View recent changes")
            print("  [4] Manage whitelist")
            print("  [5] Manage blacklist")
            print("  [6] Exit")
            
            choice = input("\nChoose mode: ").strip()
            
            if choice == '1':
                sanitizer.run_interactive()
                break
            
            elif choice == '2':
                confirm = input("Auto-fix obvious issues? (yes/no): ").strip().lower()
                if confirm == 'yes':
                    sanitizer.run_batch(auto_fix=True)
                    break
                else:
                    print("Cancelled")
            
            elif choice == '3':
                recent = sanitizer.changelog.get_latest(10)
                print(f"\nRecent changes ({len(recent)} shown):")
                for change in recent:
                    print(f"  {change['timestamp']}: {change['type']} - {change['old_name']} -> {change['new_name']}")
            
            elif choice == '4':
                print("\nWhitelist Management:")
                print("  [1] View whitelist")
                print("  [2] Add to whitelist")
                print("  [3] Remove from whitelist")
                print("  [4] Back")
                sub_choice = input("Choose: ").strip()
                
                if sub_choice == '1':
                    if sanitizer.whitelist.names:
                        for name in sorted(list(sanitizer.whitelist.names))[:20]:
                            print(f"  - {name}")
                        if len(sanitizer.whitelist.names) > 20:
                            print(f"  ... and {len(sanitizer.whitelist.names) - 20} more")
                    else:
                        print("  Whitelist is empty")
                
                elif sub_choice == '2':
                    name = input("Enter author name: ").strip()
                    notes = input("Notes (optional): ").strip()
                    sanitizer.whitelist.add(name, notes)
                    print(f"✓ Added '{name}' to whitelist")
                
                elif sub_choice == '3':
                    name = input("Enter author name to remove: ").strip()
                    sanitizer.whitelist.remove(name)
                    print(f"✓ Removed '{name}' from whitelist")
            
            elif choice == '5':
                print("\nBlacklist Management:")
                print("  [1] View blacklist")
                print("  [2] Add exact name")
                print("  [3] Add pattern")
                print("  [4] Back")
                sub_choice = input("Choose: ").strip()
                
                if sub_choice == '1':
                    if sanitizer.blacklist.exact_names:
                        print("Exact names:")
                        for name in sorted(list(sanitizer.blacklist.exact_names))[:10]:
                            print(f"  - {name}")
                    if sanitizer.blacklist.patterns:
                        print("Patterns:")
                        for item in sanitizer.blacklist.patterns[:5]:
                            print(f"  - {item['pattern']} ({item.get('reason', 'N/A')})")
                
                elif sub_choice == '2':
                    name = input("Enter author name: ").strip()
                    reason = input("Reason: ").strip()
                    sanitizer.blacklist.add_exact(name, reason)
                    print(f"✓ Added '{name}' to blacklist")
                
                elif sub_choice == '3':
                    pattern = input("Enter regex pattern: ").strip()
                    reason = input("Reason: ").strip()
                    sanitizer.blacklist.add_pattern(pattern, reason)
                    print(f"✓ Added pattern to blacklist")
            
            elif choice == '6':
                print("Exiting...")
                break
            
            else:
                print("Invalid option")
    
    finally:
        sanitizer.close()


if __name__ == "__main__":
    main(),  # The Four Loves
        'scripture': r'^\d+\s+[A-Z][a-z]+\s+\d+[:\d-]*(\s*\([A-Z]+\))?
    
    @staticmethod
    def validate(name: str) -> tuple[bool, str]:
        """
        Validate if a name matches expected format
        
        Returns:
            (is_valid, pattern_matched)
        """
        for pattern_name, pattern in NameValidator.PATTERNS.items():
            if re.match(pattern, name):
                return True, pattern_name
        
        return False, "unknown"
    
    @staticmethod
    def suggest_fixes(name: str) -> list[str]:
        """Suggest what might be wrong with a name"""
        fixes = []
        
        if name != name.strip():
            fixes.append("Remove leading/trailing whitespace")
        
        if '  ' in name:
            fixes.append("Remove extra spaces")
        
        if re.search(r'[a-z]\. [A-Z]', name):
            fixes.append("Lowercase letters should not precede periods in abbreviations")
        
        if re.search(r'([A-Z][a-z]*){3,}', name) and not re.search(r'\s', name):
            fixes.append("Name is missing spaces between parts")
        
        if name.isupper() and len(name) > 1:
            fixes.append("Name is all uppercase - should be title case")
        
        return fixes


class NameWhitelist:
    """Manage known good author names"""
    
    def __init__(self, whitelist_file: str = "author_whitelist.json"):
        self.whitelist_file = Path(whitelist_file)
        self.names = set()
        self.metadata = {}
        self.load()
    
    def load(self):
        """Load whitelist from disk"""
        if self.whitelist_file.exists():
            try:
                with open(self.whitelist_file, 'r') as f:
                    data = json.load(f)
                    self.names = set(data.get('names', []))
                    self.metadata = data.get('metadata', {})
            except:
                self.names = set()
                self.metadata = {}
    
    def save(self):
        """Save whitelist to disk"""
        with open(self.whitelist_file, 'w') as f:
            json.dump({
                'names': sorted(list(self.names)),
                'metadata': self.metadata,
                'count': len(self.names),
                'last_updated': datetime.now().isoformat()
            }, f, indent=2)
    
    def add(self, name: str, notes: str = ""):
        """Add a name to the whitelist"""
        self.names.add(name)
        if notes:
            self.metadata[name] = {'added': datetime.now().isoformat(), 'notes': notes}
        self.save()
    
    def remove(self, name: str):
        """Remove a name from whitelist"""
        self.names.discard(name)
        if name in self.metadata:
            del self.metadata[name]
        self.save()
    
    def is_whitelisted(self, name: str) -> bool:
        """Check if name is whitelisted"""
        return name in self.names
    
    def export(self, filename: str = "author_whitelist_export.json"):
        """Export whitelist"""
        with open(filename, 'w') as f:
            json.dump({
                'names': sorted(list(self.names)),
                'metadata': self.metadata,
                'count': len(self.names),
                'exported': datetime.now().isoformat()
            }, f, indent=2)
        print(f"✓ Exported {len(self.names)} whitelisted names to {filename}")


class NameBlacklist:
    """Manage known bad author name patterns"""
    
    def __init__(self, blacklist_file: str = "author_blacklist.json"):
        self.blacklist_file = Path(blacklist_file)
        self.patterns = []  # List of regex patterns
        self.exact_names = set()
        self.load()
    
    def load(self):
        """Load blacklist from disk"""
        if self.blacklist_file.exists():
            try:
                with open(self.blacklist_file, 'r') as f:
                    data = json.load(f)
                    self.patterns = data.get('patterns', [])
                    self.exact_names = set(data.get('exact_names', []))
            except:
                self.patterns = []
                self.exact_names = set()
    
    def save(self):
        """Save blacklist to disk"""
        with open(self.blacklist_file, 'w') as f:
            json.dump({
                'patterns': self.patterns,
                'exact_names': sorted(list(self.exact_names)),
                'total_patterns': len(self.patterns),
                'total_names': len(self.exact_names),
                'last_updated': datetime.now().isoformat()
            }, f, indent=2)
    
    def add_pattern(self, pattern: str, reason: str = ""):
        """Add a regex pattern to blacklist"""
        self.patterns.append({'pattern': pattern, 'reason': reason})
        self.save()
    
    def add_exact(self, name: str, reason: str = ""):
        """Add an exact name to blacklist"""
        self.exact_names.add(name)
        self.save()
    
    def is_blacklisted(self, name: str) -> tuple[bool, str]:
        """
        Check if name matches blacklist
        
        Returns:
            (is_blacklisted, reason)
        """
        # Check exact matches
        if name in self.exact_names:
            return True, "exact match in blacklist"
        
        # Check patterns
        for item in self.patterns:
            try:
                if re.search(item['pattern'], name):
                    return True, item.get('reason', 'matched pattern')
            except:
                pass
        
        return False, ""
    
    def export(self, filename: str = "author_blacklist_export.json"):
        """Export blacklist"""
        with open(filename, 'w') as f:
            json.dump({
                'patterns': self.patterns,
                'exact_names': sorted(list(self.exact_names)),
                'total_patterns': len(self.patterns),
                'total_names': len(self.exact_names),
                'exported': datetime.now().isoformat()
            }, f, indent=2)
        print(f"✓ Exported blacklist to {filename}")


class AuthorSanitizer:
    """Interactive tool for cleaning and standardizing author names"""
    
    def __init__(self):
        self.db = DB()
        self.changelog = ChangeLog()
        self.whitelist = NameWhitelist()
        self.blacklist = NameBlacklist()
        self.changes_made = []
        self.skipped = []
        self.session_start = datetime.now()
    
    def close(self):
        """Close database connection"""
        self.db.close()
    
    def needs_editing(self):
        """Get all authors marked for editing"""
        return self.db.authors.needs_edit()
    
    def is_likely_garbage(self, name: str) -> tuple[bool, list[str]]:
        """Check if author name looks suspicious/needs attention"""
        issues = []
        
        # Check blacklist first
        is_blacklisted, reason = self.blacklist.is_blacklisted(name)
        if is_blacklisted:
            issues.append(f"blacklist match ({reason})")
        
        # Check whitelist
        if self.whitelist.is_whitelisted(name):
            return False, []  # Whitelisted = good to go
        
        # Check for excessive quotation marks
        if name.count('"') > 2:
            issues.append(f"excessive quotes ({name.count('\"')} found)")
        
        # Check for malformed abbreviations (C.S.Lewis instead of C. S. Lewis)
        if re.search(r'[A-Z]\.[A-Z]\.', name) and not re.search(r'[A-Z]\. [A-Z]\.', name):
            issues.append("improper abbreviation spacing")
        
        # Check for mixed case that suggests garbage
        if re.search(r'[A-Z][a-z]*[A-Z]', name) and not re.search(r'\(', name):
            issues.append("unusual capitalization")
        
        # Check for numbers at start (scripture references)
        if re.match(r'^\d+', name) and not re.match(r'^\d+\s+[A-Za-z]+', name):
            issues.append("possible malformed scripture reference")
        
        # Check for excessive punctuation
        if name.count('.') > 4:
            issues.append("excessive periods")
        
        # Check format validity
        is_valid, pattern = NameValidator.validate(name)
        if not is_valid:
            issues.append(f"doesn't match standard patterns")
        
        return len(issues) > 0, issues
    
    def clean_quotation_marks(self, name: str) -> str:
        """Remove excessive embedded quotation marks, extracting the content"""
        # Pattern: text """""content""""" text -> text (content) text
        match = re.search(r'(\w+)\s+"{2,}(.+?)"{2,}\s+(\w+)', name)
        if match:
            before = match.group(1)
            content = match.group(2).strip()
            after = match.group(3)
            return f"{before} {after} ({content})"
        
        # Just remove quotes if no clear pattern
        return name.replace('"', '')
    
    def format_abbreviations(self, name: str) -> str:
        """Fix abbreviation spacing: C.S. Lewis -> C. S. Lewis"""
        # Find patterns like C.S. and fix to C. S.
        name = re.sub(r'([A-Z])\.([A-Z])\.', r'\1. \2.', name)
        # Fix spacing after abbreviations if needed
        name = re.sub(r'([A-Z]\.) ([A-Z]\.)', r'\1 \2', name)
        return name.strip()
    
    def format_title_case(self, name: str) -> str:
        """Convert to title case, respecting articles and prepositions"""
        # Words that should be lowercase in titles (unless first word)
        lowercase_words = {'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        
        # Preserve parenthetical content
        paren_match = re.match(r'^(.*?)(\(.+\))$', name)
        if paren_match:
            title = paren_match.group(1).strip()
            paren = paren_match.group(2)
            name = title
            preserve_paren = paren
        else:
            preserve_paren = None
        
        # Split and process words
        words = name.split()
        result = []
        
        for i, word in enumerate(words):
            if i == 0 or word.lower() not in lowercase_words:
                result.append(word.capitalize())
            else:
                result.append(word.lower())
        
        final = ' '.join(result)
        if preserve_paren:
            final = f"{final} {preserve_paren}"
        
        return final
    
    def format_scripture_reference(self, name: str) -> str:
        """Format scripture references: 1 Kings 1:12-14 or 1 Kings 1 (NIV)"""
        # Already well-formatted
        if re.match(r'^\d+\s+[A-Za-z]+\s+\d+', name):
            return name
        return name
    
    def suggest_format(self, name: str) -> str:
        """Suggest how the name should be formatted"""
        original = name
        
        # Clean garbage quotation marks first
        if '"""' in name or '""""' in name:
            name = self.clean_quotation_marks(name)
        
        # Check if it's a scripture reference
        if re.match(r'^\d+\s+[A-Z]', name):
            return self.format_scripture_reference(name)
        
        # Check if it looks like a title (multiple capitals, or keywords)
        is_title = (
            name.isupper() or 
            re.search(r'\b(The|A|An|And|Or)\b', name) or
            ': ' in name or  # Subtitles
            name.count(' ') > 2 and sum(1 for c in name if c.isupper()) > 2
        )
        
        if is_title and not re.match(r'^[A-Z]\.\s', name):  # Not an abbreviation
            return self.format_title_case(name)
        
        # Regular name - fix abbreviations
        return self.format_abbreviations(name)
    
    def print_author(self, author: Author) -> None:
        """Pretty print author info"""
        print(f"\n{'='*80}")
        print(f"ID: {author.id}")
        print(f"Name: {author.name}")
        
        # Validate current name
        is_valid, pattern = NameValidator.validate(author.name)
        if is_valid:
            print(f"Status: ✓ Valid ({pattern})")
        else:
            print(f"Status: ✗ Invalid format")
            fixes = NameValidator.suggest_fixes(author.name)
            if fixes:
                print("Suggested fixes:")
                for fix in fixes:
                    print(f"  - {fix}")
        
        if author.birth_year or author.death_year:
            years = f"{author.birth_year or '?'}-{author.death_year or '?'}"
            print(f"Years: {years}")
        if author.profession:
            print(f"Profession: {author.profession}")
        if author.nationality:
            print(f"Nationality: {author.nationality}")
        print(f"Quotes: {len(author.quotes)}")
        if author.quotes:
            print(f"Sample quote: {author.quotes[0].text[:70]}...")
        print(f"{'='*80}")
    
    def author_exists(self, name: str) -> bool:
        """Check if author with this name already exists"""
        try:
            return self.db.authors.get_by_name(name) is not None
        except:
            return False
    
    def merge_authors(self, from_author: Author, to_author: Author) -> None:
        """Move all quotes from one author to another, then delete the from_author"""
        print(f"\nMerging {len(from_author.quotes)} quotes from '{from_author.name}' to '{to_author.name}'...")
        
        # Move quotes
        for quote in from_author.quotes[:]:  # Use slice to avoid modification during iteration
            quote.author = to_author
        
        self.db.commit()
        
        # Delete the old author
        old_id = from_author.id
        self.db.session.delete(from_author)
        self.db.commit()
        
        # Log the merge
        self.changelog.add('MERGED', old_id, from_author.name, to_author.name, merged_with=to_author.name)
        
        print(f"✓ Merge complete!")
    
    def process_author(self, author: Author) -> None:
        """Interactive processing for a single author"""
        is_garbage, issues = self.is_likely_garbage(author.name)
        
        if is_garbage:
            print(f"\n⚠ Issues detected: {', '.join(issues)}")
        
        self.print_author(author)
        
        # Show suggestion
        suggestion = self.suggest_format(author.name)
        if suggestion != author.name:
            print(f"\nSuggested format: {suggestion}")
        else:
            print(f"\nNo format changes suggested.")
        
        while True:
            print("\nOptions:")
            print("  [1] Keep as is")
            if suggestion != author.name:
                print("  [2] Accept suggestion")
            print("  [3] Manual edit")
            print("  [4] Add to whitelist (skip)")
            print("  [5] Add to blacklist")
            print("  [6] Delete author and all quotes")
            print("  [7] Skip this author")
            
            choice = input("\nChoose option: ").strip()
            
            if choice == '1':
                self.skipped.append(author.name)
                print("✓ Keeping as is")
                return
            
            elif choice == '2' and suggestion != author.name:
                self._apply_change(author, suggestion)
                return
            
            elif choice == '3':
                new_name = input("Enter correct author name: ").strip()
                if new_name:
                    self._apply_change(author, new_name)
                    return
                else:
                    print("Name cannot be empty")
            
            elif choice == '4':
                self.whitelist.add(author.name, "User approved during sanitization")
                print(f"✓ Added '{author.name}' to whitelist")
                self.skipped.append(author.name)
                return
            
            elif choice == '5':
                reason = input("Reason for blacklisting: ").strip()
                self.blacklist.add_exact(author.name, reason or "Garbage/spam author")
                print(f"✓ Added '{author.name}' to blacklist")
                
                delete = input("Delete this author and quotes? (yes/no): ").strip().lower()
                if delete == 'yes':
                    self.db.session.delete(author)
                    self.db.commit()
                    print(f"✓ Deleted")
                    self.changes_made.append(f"DELETED: {author.name}")
                return
            
            elif choice == '6':
                confirm = input(f"Delete '{author.name}' and its {len(author.quotes)} quotes? (yes/no): ").strip().lower()
                if confirm == 'yes':
                    self.db.session.delete(author)
                    self.db.commit()
                    print(f"✓ Deleted")
                    self.changes_made.append(f"DELETED: {author.name}")
                    self.changelog.add('DELETED', author.id, author.name, "")
                    return
                else:
                    print("Cancelled")
            
            elif choice == '7':
                self.skipped.append(author.name)
                print("✓ Skipped")
                return
            
            else:
                print("Invalid option")
    
    def _apply_change(self, author: Author, new_name: str) -> None:
        """Apply a name change, handling duplicates"""
        new_name = new_name.strip()
        
        if new_name == author.name:
            print("No change made")
            return
        
        # Check if new name already exists
        existing = self.db.authors.get_by_name(new_name)
        
        if existing and existing.id != author.id:
            print(f"\n⚠ Author '{new_name}' already exists!")
            print(f"  Existing author has {len(existing.quotes)} quotes")
            print(f"  Current author '{author.name}' has {len(author.quotes)} quotes")
            
            merge_choice = input("\nMerge these authors? (yes/no): ").strip().lower()
            if merge_choice == 'yes':
                self.merge_authors(author, existing)
                self.changes_made.append(f"MERGED: '{author.name}' -> '{new_name}'")
            else:
                print("Cancelled - no changes made")
            return
        
        # Safe to rename
        old_name = author.name
        author.name = new_name
        author.unmark_for_edit()  # Remove the edit flag
        self.db.commit()
        
        # Log change
        self.changelog.add('RENAMED', author.id, old_name, new_name)
        
        print(f"✓ Changed: '{old_name}' -> '{new_name}'")
        self.changes_made.append(f"RENAMED: '{old_name}' -> '{new_name}'")
    
    def undo_last_change(self):
        """Undo the most recent change"""
        recent = self.changelog.get_latest(1)
        if not recent:
            print("No changes to undo")
            return
        
        change = recent[0]
        print(f"\nUndoing: {change}")
        print("Note: Undo is not yet implemented in the database layer")
        print("You would need to manually revert this change or restore from backup")
    
    def run_interactive(self):
        """Main interactive loop"""
        authors = self.needs_editing()
        
        if not authors:
            print("✓ No authors need editing!")
            return
        
        print(f"\nFound {len(authors)} authors needing editing")
        print("="*80)
        
        for i, author in enumerate(authors, 1):
            print(f"\n[{i}/{len(authors)}]")
            self.process_author(author)
        
        self.print_summary()
    
    def run_batch(self, auto_fix=False):
        """
        Run in batch mode - optionally auto-fix obvious issues
        
        Args:
            auto_fix: If True, automatically apply suggestions without confirmation
        """
        authors = self.needs_editing()
        
        if not authors:
            print("✓ No authors need editing!")
            return
        
        print(f"\nProcessing {len(authors)} authors...")
        print("="*80)
        
        for i, author in enumerate(authors, 1):
            is_garbage, issues = self.is_likely_garbage(author.name)
            suggestion = self.suggest_format(author.name)
            
            if suggestion != author.name:
                if auto_fix:
                    print(f"[{i}/{len(authors)}] Auto-fixing: {author.name}")
                    if not self.author_exists(suggestion):
                        self._apply_change(author, suggestion)
                    else:
                        existing = self.db.authors.get_by_name(suggestion)
                        self.merge_authors(author, existing)
                else:
                    print(f"[{i}/{len(authors)}] Review needed: {author.name}")
        
        self.print_summary()
    
    def print_summary(self):
        """Print summary of changes"""
        print(f"\n{'='*80}")
        print("SUMMARY")
        print(f"{'='*80}")
        print(f"Session started: {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Changes made: {len(self.changes_made)}")
        for change in self.changes_made:
            print(f"  ✓ {change}")
        
        if self.skipped:
            print(f"\nSkipped: {len(self.skipped)}")
            for name in self.skipped[:5]:
                print(f"  - {name}")
            if len(self.skipped) > 5:
                print(f"  ... and {len(self.skipped) - 5} more")
        
        # Export options
        print("\nExport options:")
        export_choice = input("Export changelog? (yes/no): ").strip().lower()
        if export_choice == 'yes':
            self.changelog.export()
        
        export_choice = input("Export whitelist? (yes/no): ").strip().lower()
        if export_choice == 'yes':
            self.whitelist.export()
        
        export_choice = input("Export blacklist? (yes/no): ").strip().lower()
        if export_choice == 'yes':
            self.blacklist.export()


def main():
    """Main entry point"""
    print("Author Name Sanitizer")
    print("="*80)
    
    sanitizer = AuthorSanitizer()
    
    try:
        while True:
            print("\nModes:")
            print("  [1] Interactive mode (review each author)")
            print("  [2] Batch mode (auto-fix obvious issues)")
            print("  [3] View recent changes")
            print("  [4] Manage whitelist")
            print("  [5] Manage blacklist")
            print("  [6] Exit")
            
            choice = input("\nChoose mode: ").strip()
            
            if choice == '1':
                sanitizer.run_interactive()
                break
            
            elif choice == '2':
                confirm = input("Auto-fix obvious issues? (yes/no): ").strip().lower()
                if confirm == 'yes':
                    sanitizer.run_batch(auto_fix=True)
                    break
                else:
                    print("Cancelled")
            
            elif choice == '3':
                recent = sanitizer.changelog.get_latest(10)
                print(f"\nRecent changes ({len(recent)} shown):")
                for change in recent:
                    print(f"  {change['timestamp']}: {change['type']} - {change['old_name']} -> {change['new_name']}")
            
            elif choice == '4':
                print("\nWhitelist Management:")
                print("  [1] View whitelist")
                print("  [2] Add to whitelist")
                print("  [3] Remove from whitelist")
                print("  [4] Back")
                sub_choice = input("Choose: ").strip()
                
                if sub_choice == '1':
                    if sanitizer.whitelist.names:
                        for name in sorted(list(sanitizer.whitelist.names))[:20]:
                            print(f"  - {name}")
                        if len(sanitizer.whitelist.names) > 20:
                            print(f"  ... and {len(sanitizer.whitelist.names) - 20} more")
                    else:
                        print("  Whitelist is empty")
                
                elif sub_choice == '2':
                    name = input("Enter author name: ").strip()
                    notes = input("Notes (optional): ").strip()
                    sanitizer.whitelist.add(name, notes)
                    print(f"✓ Added '{name}' to whitelist")
                
                elif sub_choice == '3':
                    name = input("Enter author name to remove: ").strip()
                    sanitizer.whitelist.remove(name)
                    print(f"✓ Removed '{name}' from whitelist")
            
            elif choice == '5':
                print("\nBlacklist Management:")
                print("  [1] View blacklist")
                print("  [2] Add exact name")
                print("  [3] Add pattern")
                print("  [4] Back")
                sub_choice = input("Choose: ").strip()
                
                if sub_choice == '1':
                    if sanitizer.blacklist.exact_names:
                        print("Exact names:")
                        for name in sorted(list(sanitizer.blacklist.exact_names))[:10]:
                            print(f"  - {name}")
                    if sanitizer.blacklist.patterns:
                        print("Patterns:")
                        for item in sanitizer.blacklist.patterns[:5]:
                            print(f"  - {item['pattern']} ({item.get('reason', 'N/A')})")
                
                elif sub_choice == '2':
                    name = input("Enter author name: ").strip()
                    reason = input("Reason: ").strip()
                    sanitizer.blacklist.add_exact(name, reason)
                    print(f"✓ Added '{name}' to blacklist")
                
                elif sub_choice == '3':
                    pattern = input("Enter regex pattern: ").strip()
                    reason = input("Reason: ").strip()
                    sanitizer.blacklist.add_pattern(pattern, reason)
                    print(f"✓ Added pattern to blacklist")
            
            elif choice == '6':
                print("Exiting...")
                break
            
            else:
                print("Invalid option")
    
    finally:
        sanitizer.close()


if __name__ == "__main__":
    main(),  # 1 Kings 1:12-14
    }
    
    @staticmethod
    def validate(name: str) -> tuple[bool, str]:
        """
        Validate if a name matches expected format
        
        Returns:
            (is_valid, pattern_matched)
        """
        for pattern_name, pattern in NameValidator.PATTERNS.items():
            if re.match(pattern, name):
                return True, pattern_name
        
        return False, "unknown"
    
    @staticmethod
    def suggest_fixes(name: str) -> list[str]:
        """Suggest what might be wrong with a name"""
        fixes = []
        
        if name != name.strip():
            fixes.append("Remove leading/trailing whitespace")
        
        if '  ' in name:
            fixes.append("Remove extra spaces")
        
        if re.search(r'[a-z]\. [A-Z]', name):
            fixes.append("Lowercase letters should not precede periods in abbreviations")
        
        if re.search(r'([A-Z][a-z]*){3,}', name) and not re.search(r'\s', name):
            fixes.append("Name is missing spaces between parts")
        
        if name.isupper() and len(name) > 1:
            fixes.append("Name is all uppercase - should be title case")
        
        return fixes


class NameWhitelist:
    """Manage known good author names"""
    
    def __init__(self, whitelist_file: str = "author_whitelist.json"):
        self.whitelist_file = Path(whitelist_file)
        self.names = set()
        self.metadata = {}
        self.load()
    
    def load(self):
        """Load whitelist from disk"""
        if self.whitelist_file.exists():
            try:
                with open(self.whitelist_file, 'r') as f:
                    data = json.load(f)
                    self.names = set(data.get('names', []))
                    self.metadata = data.get('metadata', {})
            except:
                self.names = set()
                self.metadata = {}
    
    def save(self):
        """Save whitelist to disk"""
        with open(self.whitelist_file, 'w') as f:
            json.dump({
                'names': sorted(list(self.names)),
                'metadata': self.metadata,
                'count': len(self.names),
                'last_updated': datetime.now().isoformat()
            }, f, indent=2)
    
    def add(self, name: str, notes: str = ""):
        """Add a name to the whitelist"""
        self.names.add(name)
        if notes:
            self.metadata[name] = {'added': datetime.now().isoformat(), 'notes': notes}
        self.save()
    
    def remove(self, name: str):
        """Remove a name from whitelist"""
        self.names.discard(name)
        if name in self.metadata:
            del self.metadata[name]
        self.save()
    
    def is_whitelisted(self, name: str) -> bool:
        """Check if name is whitelisted"""
        return name in self.names
    
    def export(self, filename: str = "author_whitelist_export.json"):
        """Export whitelist"""
        with open(filename, 'w') as f:
            json.dump({
                'names': sorted(list(self.names)),
                'metadata': self.metadata,
                'count': len(self.names),
                'exported': datetime.now().isoformat()
            }, f, indent=2)
        print(f"✓ Exported {len(self.names)} whitelisted names to {filename}")


class NameBlacklist:
    """Manage known bad author name patterns"""
    
    def __init__(self, blacklist_file: str = "author_blacklist.json"):
        self.blacklist_file = Path(blacklist_file)
        self.patterns = []  # List of regex patterns
        self.exact_names = set()
        self.load()
    
    def load(self):
        """Load blacklist from disk"""
        if self.blacklist_file.exists():
            try:
                with open(self.blacklist_file, 'r') as f:
                    data = json.load(f)
                    self.patterns = data.get('patterns', [])
                    self.exact_names = set(data.get('exact_names', []))
            except:
                self.patterns = []
                self.exact_names = set()
    
    def save(self):
        """Save blacklist to disk"""
        with open(self.blacklist_file, 'w') as f:
            json.dump({
                'patterns': self.patterns,
                'exact_names': sorted(list(self.exact_names)),
                'total_patterns': len(self.patterns),
                'total_names': len(self.exact_names),
                'last_updated': datetime.now().isoformat()
            }, f, indent=2)
    
    def add_pattern(self, pattern: str, reason: str = ""):
        """Add a regex pattern to blacklist"""
        self.patterns.append({'pattern': pattern, 'reason': reason})
        self.save()
    
    def add_exact(self, name: str, reason: str = ""):
        """Add an exact name to blacklist"""
        self.exact_names.add(name)
        self.save()
    
    def is_blacklisted(self, name: str) -> tuple[bool, str]:
        """
        Check if name matches blacklist
        
        Returns:
            (is_blacklisted, reason)
        """
        # Check exact matches
        if name in self.exact_names:
            return True, "exact match in blacklist"
        
        # Check patterns
        for item in self.patterns:
            try:
                if re.search(item['pattern'], name):
                    return True, item.get('reason', 'matched pattern')
            except:
                pass
        
        return False, ""
    
    def export(self, filename: str = "author_blacklist_export.json"):
        """Export blacklist"""
        with open(filename, 'w') as f:
            json.dump({
                'patterns': self.patterns,
                'exact_names': sorted(list(self.exact_names)),
                'total_patterns': len(self.patterns),
                'total_names': len(self.exact_names),
                'exported': datetime.now().isoformat()
            }, f, indent=2)
        print(f"✓ Exported blacklist to {filename}")


class AuthorSanitizer:
    """Interactive tool for cleaning and standardizing author names"""
    
    def __init__(self):
        self.db = DB()
        self.changelog = ChangeLog()
        self.whitelist = NameWhitelist()
        self.blacklist = NameBlacklist()
        self.changes_made = []
        self.skipped = []
        self.session_start = datetime.now()
    
    def close(self):
        """Close database connection"""
        self.db.close()
    
    def needs_editing(self):
        """Get all authors marked for editing"""
        return self.db.authors.needs_edit()
    
    def is_likely_garbage(self, name: str) -> tuple[bool, list[str]]:
        """Check if author name looks suspicious/needs attention"""
        issues = []
        
        # Check blacklist first
        is_blacklisted, reason = self.blacklist.is_blacklisted(name)
        if is_blacklisted:
            issues.append(f"blacklist match ({reason})")
        
        # Check whitelist
        if self.whitelist.is_whitelisted(name):
            return False, []  # Whitelisted = good to go
        
        # Check for excessive quotation marks
        if name.count('"') > 2:
            issues.append(f"excessive quotes ({name.count('\"')} found)")
        
        # Check for malformed abbreviations (C.S.Lewis instead of C. S. Lewis)
        if re.search(r'[A-Z]\.[A-Z]\.', name) and not re.search(r'[A-Z]\. [A-Z]\.', name):
            issues.append("improper abbreviation spacing")
        
        # Check for mixed case that suggests garbage
        if re.search(r'[A-Z][a-z]*[A-Z]', name) and not re.search(r'\(', name):
            issues.append("unusual capitalization")
        
        # Check for numbers at start (scripture references)
        if re.match(r'^\d+', name) and not re.match(r'^\d+\s+[A-Za-z]+', name):
            issues.append("possible malformed scripture reference")
        
        # Check for excessive punctuation
        if name.count('.') > 4:
            issues.append("excessive periods")
        
        # Check format validity
        is_valid, pattern = NameValidator.validate(name)
        if not is_valid:
            issues.append(f"doesn't match standard patterns")
        
        return len(issues) > 0, issues
    
    def clean_quotation_marks(self, name: str) -> str:
        """Remove excessive embedded quotation marks, extracting the content"""
        # Pattern: text """""content""""" text -> text (content) text
        match = re.search(r'(\w+)\s+"{2,}(.+?)"{2,}\s+(\w+)', name)
        if match:
            before = match.group(1)
            content = match.group(2).strip()
            after = match.group(3)
            return f"{before} {after} ({content})"
        
        # Just remove quotes if no clear pattern
        return name.replace('"', '')
    
    def format_abbreviations(self, name: str) -> str:
        """Fix abbreviation spacing: C.S. Lewis -> C. S. Lewis"""
        # Find patterns like C.S. and fix to C. S.
        name = re.sub(r'([A-Z])\.([A-Z])\.', r'\1. \2.', name)
        # Fix spacing after abbreviations if needed
        name = re.sub(r'([A-Z]\.) ([A-Z]\.)', r'\1 \2', name)
        return name.strip()
    
    def format_title_case(self, name: str) -> str:
        """Convert to title case, respecting articles and prepositions"""
        # Words that should be lowercase in titles (unless first word)
        lowercase_words = {'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        
        # Preserve parenthetical content
        paren_match = re.match(r'^(.*?)(\(.+\))$', name)
        if paren_match:
            title = paren_match.group(1).strip()
            paren = paren_match.group(2)
            name = title
            preserve_paren = paren
        else:
            preserve_paren = None
        
        # Split and process words
        words = name.split()
        result = []
        
        for i, word in enumerate(words):
            if i == 0 or word.lower() not in lowercase_words:
                result.append(word.capitalize())
            else:
                result.append(word.lower())
        
        final = ' '.join(result)
        if preserve_paren:
            final = f"{final} {preserve_paren}"
        
        return final
    
    def format_scripture_reference(self, name: str) -> str:
        """Format scripture references: 1 Kings 1:12-14 or 1 Kings 1 (NIV)"""
        # Already well-formatted
        if re.match(r'^\d+\s+[A-Za-z]+\s+\d+', name):
            return name
        return name
    
    def suggest_format(self, name: str) -> str:
        """Suggest how the name should be formatted"""
        original = name
        
        # Clean garbage quotation marks first
        if '"""' in name or '""""' in name:
            name = self.clean_quotation_marks(name)
        
        # Check if it's a scripture reference
        if re.match(r'^\d+\s+[A-Z]', name):
            return self.format_scripture_reference(name)
        
        # Check if it looks like a title (multiple capitals, or keywords)
        is_title = (
            name.isupper() or 
            re.search(r'\b(The|A|An|And|Or)\b', name) or
            ': ' in name or  # Subtitles
            name.count(' ') > 2 and sum(1 for c in name if c.isupper()) > 2
        )
        
        if is_title and not re.match(r'^[A-Z]\.\s', name):  # Not an abbreviation
            return self.format_title_case(name)
        
        # Regular name - fix abbreviations
        return self.format_abbreviations(name)
    
    def print_author(self, author: Author) -> None:
        """Pretty print author info"""
        print(f"\n{'='*80}")
        print(f"ID: {author.id}")
        print(f"Name: {author.name}")
        
        # Validate current name
        is_valid, pattern = NameValidator.validate(author.name)
        if is_valid:
            print(f"Status: ✓ Valid ({pattern})")
        else:
            print(f"Status: ✗ Invalid format")
            fixes = NameValidator.suggest_fixes(author.name)
            if fixes:
                print("Suggested fixes:")
                for fix in fixes:
                    print(f"  - {fix}")
        
        if author.birth_year or author.death_year:
            years = f"{author.birth_year or '?'}-{author.death_year or '?'}"
            print(f"Years: {years}")
        if author.profession:
            print(f"Profession: {author.profession}")
        if author.nationality:
            print(f"Nationality: {author.nationality}")
        print(f"Quotes: {len(author.quotes)}")
        if author.quotes:
            print(f"Sample quote: {author.quotes[0].text[:70]}...")
        print(f"{'='*80}")
    
    def author_exists(self, name: str) -> bool:
        """Check if author with this name already exists"""
        try:
            return self.db.authors.get_by_name(name) is not None
        except:
            return False
    
    def merge_authors(self, from_author: Author, to_author: Author) -> None:
        """Move all quotes from one author to another, then delete the from_author"""
        print(f"\nMerging {len(from_author.quotes)} quotes from '{from_author.name}' to '{to_author.name}'...")
        
        # Move quotes
        for quote in from_author.quotes[:]:  # Use slice to avoid modification during iteration
            quote.author = to_author
        
        self.db.commit()
        
        # Delete the old author
        old_id = from_author.id
        self.db.session.delete(from_author)
        self.db.commit()
        
        # Log the merge
        self.changelog.add('MERGED', old_id, from_author.name, to_author.name, merged_with=to_author.name)
        
        print(f"✓ Merge complete!")
    
    def process_author(self, author: Author) -> None:
        """Interactive processing for a single author"""
        is_garbage, issues = self.is_likely_garbage(author.name)
        
        if is_garbage:
            print(f"\n⚠ Issues detected: {', '.join(issues)}")
        
        self.print_author(author)
        
        # Show suggestion
        suggestion = self.suggest_format(author.name)
        if suggestion != author.name:
            print(f"\nSuggested format: {suggestion}")
        else:
            print(f"\nNo format changes suggested.")
        
        while True:
            print("\nOptions:")
            print("  [1] Keep as is")
            if suggestion != author.name:
                print("  [2] Accept suggestion")
            print("  [3] Manual edit")
            print("  [4] Add to whitelist (skip)")
            print("  [5] Add to blacklist")
            print("  [6] Delete author and all quotes")
            print("  [7] Skip this author")
            
            choice = input("\nChoose option: ").strip()
            
            if choice == '1':
                self.skipped.append(author.name)
                print("✓ Keeping as is")
                return
            
            elif choice == '2' and suggestion != author.name:
                self._apply_change(author, suggestion)
                return
            
            elif choice == '3':
                new_name = input("Enter correct author name: ").strip()
                if new_name:
                    self._apply_change(author, new_name)
                    return
                else:
                    print("Name cannot be empty")
            
            elif choice == '4':
                self.whitelist.add(author.name, "User approved during sanitization")
                print(f"✓ Added '{author.name}' to whitelist")
                self.skipped.append(author.name)
                return
            
            elif choice == '5':
                reason = input("Reason for blacklisting: ").strip()
                self.blacklist.add_exact(author.name, reason or "Garbage/spam author")
                print(f"✓ Added '{author.name}' to blacklist")
                
                delete = input("Delete this author and quotes? (yes/no): ").strip().lower()
                if delete == 'yes':
                    self.db.session.delete(author)
                    self.db.commit()
                    print(f"✓ Deleted")
                    self.changes_made.append(f"DELETED: {author.name}")
                return
            
            elif choice == '6':
                confirm = input(f"Delete '{author.name}' and its {len(author.quotes)} quotes? (yes/no): ").strip().lower()
                if confirm == 'yes':
                    self.db.session.delete(author)
                    self.db.commit()
                    print(f"✓ Deleted")
                    self.changes_made.append(f"DELETED: {author.name}")
                    self.changelog.add('DELETED', author.id, author.name, "")
                    return
                else:
                    print("Cancelled")
            
            elif choice == '7':
                self.skipped.append(author.name)
                print("✓ Skipped")
                return
            
            else:
                print("Invalid option")
    
    def _apply_change(self, author: Author, new_name: str) -> None:
        """Apply a name change, handling duplicates"""
        new_name = new_name.strip()
        
        if new_name == author.name:
            print("No change made")
            return
        
        # Check if new name already exists
        existing = self.db.authors.get_by_name(new_name)
        
        if existing and existing.id != author.id:
            print(f"\n⚠ Author '{new_name}' already exists!")
            print(f"  Existing author has {len(existing.quotes)} quotes")
            print(f"  Current author '{author.name}' has {len(author.quotes)} quotes")
            
            merge_choice = input("\nMerge these authors? (yes/no): ").strip().lower()
            if merge_choice == 'yes':
                self.merge_authors(author, existing)
                self.changes_made.append(f"MERGED: '{author.name}' -> '{new_name}'")
            else:
                print("Cancelled - no changes made")
            return
        
        # Safe to rename
        old_name = author.name
        author.name = new_name
        author.unmark_for_edit()  # Remove the edit flag
        self.db.commit()
        
        # Log change
        self.changelog.add('RENAMED', author.id, old_name, new_name)
        
        print(f"✓ Changed: '{old_name}' -> '{new_name}'")
        self.changes_made.append(f"RENAMED: '{old_name}' -> '{new_name}'")
    
    def undo_last_change(self):
        """Undo the most recent change"""
        recent = self.changelog.get_latest(1)
        if not recent:
            print("No changes to undo")
            return
        
        change = recent[0]
        print(f"\nUndoing: {change}")
        print("Note: Undo is not yet implemented in the database layer")
        print("You would need to manually revert this change or restore from backup")
    
    def run_interactive(self):
        """Main interactive loop"""
        authors = self.needs_editing()
        
        if not authors:
            print("✓ No authors need editing!")
            return
        
        print(f"\nFound {len(authors)} authors needing editing")
        print("="*80)
        
        for i, author in enumerate(authors, 1):
            print(f"\n[{i}/{len(authors)}]")
            self.process_author(author)
        
        self.print_summary()
    
    def run_batch(self, auto_fix=False):
        """
        Run in batch mode - optionally auto-fix obvious issues
        
        Args:
            auto_fix: If True, automatically apply suggestions without confirmation
        """
        authors = self.needs_editing()
        
        if not authors:
            print("✓ No authors need editing!")
            return
        
        print(f"\nProcessing {len(authors)} authors...")
        print("="*80)
        
        for i, author in enumerate(authors, 1):
            is_garbage, issues = self.is_likely_garbage(author.name)
            suggestion = self.suggest_format(author.name)
            
            if suggestion != author.name:
                if auto_fix:
                    print(f"[{i}/{len(authors)}] Auto-fixing: {author.name}")
                    if not self.author_exists(suggestion):
                        self._apply_change(author, suggestion)
                    else:
                        existing = self.db.authors.get_by_name(suggestion)
                        self.merge_authors(author, existing)
                else:
                    print(f"[{i}/{len(authors)}] Review needed: {author.name}")
        
        self.print_summary()
    
    def print_summary(self):
        """Print summary of changes"""
        print(f"\n{'='*80}")
        print("SUMMARY")
        print(f"{'='*80}")
        print(f"Session started: {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Changes made: {len(self.changes_made)}")
        for change in self.changes_made:
            print(f"  ✓ {change}")
        
        if self.skipped:
            print(f"\nSkipped: {len(self.skipped)}")
            for name in self.skipped[:5]:
                print(f"  - {name}")
            if len(self.skipped) > 5:
                print(f"  ... and {len(self.skipped) - 5} more")
        
        # Export options
        print("\nExport options:")
        export_choice = input("Export changelog? (yes/no): ").strip().lower()
        if export_choice == 'yes':
            self.changelog.export()
        
        export_choice = input("Export whitelist? (yes/no): ").strip().lower()
        if export_choice == 'yes':
            self.whitelist.export()
        
        export_choice = input("Export blacklist? (yes/no): ").strip().lower()
        if export_choice == 'yes':
            self.blacklist.export()


def main():
    """Main entry point"""
    print("Author Name Sanitizer")
    print("="*80)
    
    sanitizer = AuthorSanitizer()
    
    try:
        while True:
            print("\nModes:")
            print("  [1] Interactive mode (review each author)")
            print("  [2] Batch mode (auto-fix obvious issues)")
            print("  [3] View recent changes")
            print("  [4] Manage whitelist")
            print("  [5] Manage blacklist")
            print("  [6] Exit")
            
            choice = input("\nChoose mode: ").strip()
            
            if choice == '1':
                sanitizer.run_interactive()
                break
            
            elif choice == '2':
                confirm = input("Auto-fix obvious issues? (yes/no): ").strip().lower()
                if confirm == 'yes':
                    sanitizer.run_batch(auto_fix=True)
                    break
                else:
                    print("Cancelled")
            
            elif choice == '3':
                recent = sanitizer.changelog.get_latest(10)
                print(f"\nRecent changes ({len(recent)} shown):")
                for change in recent:
                    print(f"  {change['timestamp']}: {change['type']} - {change['old_name']} -> {change['new_name']}")
            
            elif choice == '4':
                print("\nWhitelist Management:")
                print("  [1] View whitelist")
                print("  [2] Add to whitelist")
                print("  [3] Remove from whitelist")
                print("  [4] Back")
                sub_choice = input("Choose: ").strip()
                
                if sub_choice == '1':
                    if sanitizer.whitelist.names:
                        for name in sorted(list(sanitizer.whitelist.names))[:20]:
                            print(f"  - {name}")
                        if len(sanitizer.whitelist.names) > 20:
                            print(f"  ... and {len(sanitizer.whitelist.names) - 20} more")
                    else:
                        print("  Whitelist is empty")
                
                elif sub_choice == '2':
                    name = input("Enter author name: ").strip()
                    notes = input("Notes (optional): ").strip()
                    sanitizer.whitelist.add(name, notes)
                    print(f"✓ Added '{name}' to whitelist")
                
                elif sub_choice == '3':
                    name = input("Enter author name to remove: ").strip()
                    sanitizer.whitelist.remove(name)
                    print(f"✓ Removed '{name}' from whitelist")
            
            elif choice == '5':
                print("\nBlacklist Management:")
                print("  [1] View blacklist")
                print("  [2] Add exact name")
                print("  [3] Add pattern")
                print("  [4] Back")
                sub_choice = input("Choose: ").strip()
                
                if sub_choice == '1':
                    if sanitizer.blacklist.exact_names:
                        print("Exact names:")
                        for name in sorted(list(sanitizer.blacklist.exact_names))[:10]:
                            print(f"  - {name}")
                    if sanitizer.blacklist.patterns:
                        print("Patterns:")
                        for item in sanitizer.blacklist.patterns[:5]:
                            print(f"  - {item['pattern']} ({item.get('reason', 'N/A')})")
                
                elif sub_choice == '2':
                    name = input("Enter author name: ").strip()
                    reason = input("Reason: ").strip()
                    sanitizer.blacklist.add_exact(name, reason)
                    print(f"✓ Added '{name}' to blacklist")
                
                elif sub_choice == '3':
                    pattern = input("Enter regex pattern: ").strip()
                    reason = input("Reason: ").strip()
                    sanitizer.blacklist.add_pattern(pattern, reason)
                    print(f"✓ Added pattern to blacklist")
            
            elif choice == '6':
                print("Exiting...")
                break
            
            else:
                print("Invalid option")
    
    finally:
        sanitizer.close()


if __name__ == "__main__":
    main()