"""Candidate lookup system for matching transaction data with candidate information."""

import csv
import logging
import re
from typing import Dict, List, Optional, Any, Tuple, TYPE_CHECKING
from collections import defaultdict

if TYPE_CHECKING:
    from .committee_lookup import CommitteeLookup

logger = logging.getLogger(__name__)


def normalize_name(name: str) -> str:
    """
    Normalize a name for matching purposes.
    
    Removes party designations, standardizes case, removes extra spaces,
    and handles common variations.
    
    Args:
        name: Name string to normalize
        
    Returns:
        Normalized name string
    """
    if not name:
        return ""
    
    # Remove party designations in parentheses
    name = re.sub(r'\([^)]*\)', '', name)
    
    # Remove common suffixes
    name = re.sub(r'\s+,\s*(Jr\.?|Sr\.?|II|III|IV|V)$', '', name, flags=re.IGNORECASE)
    
    # Standardize case and remove extra spaces
    name = ' '.join(name.split())
    name = name.strip()
    
    # Remove leading/trailing commas
    name = name.strip(',').strip()
    
    return name


def build_full_name(first: str, last: str, middle: str = '') -> str:
    """
    Build a full name from components in "Last, First Middle" format.
    
    Args:
        first: First name
        last: Last name
        middle: Middle name (optional)
        
    Returns:
        Full name in "Last, First Middle" format
    """
    parts = [last.strip(), first.strip()]
    if middle and middle.strip():
        parts.append(middle.strip())
    return ', '.join(parts)


def parse_name_components(name: str) -> Tuple[str, str, str]:
    """
    Parse a name string into first, last, and middle components.
    
    Handles formats like "Last, First Middle" or "First Middle Last"
    
    Args:
        name: Name string to parse
        
    Returns:
        Tuple of (first, last, middle) names
    """
    name = normalize_name(name)
    
    # Try "Last, First Middle" format first
    if ',' in name:
        parts = [p.strip() for p in name.split(',', 1)]
        if len(parts) == 2:
            last = parts[0]
            first_middle = parts[1].split()
            if len(first_middle) >= 1:
                first = first_middle[0]
                middle = ' '.join(first_middle[1:]) if len(first_middle) > 1 else ''
                return (first, last, middle)
    
    # Try "First Middle Last" format
    parts = name.split()
    if len(parts) >= 2:
        first = parts[0]
        last = parts[-1]
        middle = ' '.join(parts[1:-1]) if len(parts) > 2 else ''
        return (first, last, middle)
    
    # Fallback: assume single word is last name
    if len(parts) == 1:
        return ('', parts[0], '')
    
    return ('', '', '')


class CandidateLookup:
    """
    Manages candidate data for matching with transaction records.
    
    This class loads candidate data from CSV files, builds indexes for fast lookup,
    and provides methods to match candidate names with transaction recipient/spender names.
    """
    
    def __init__(
        self,
        auto_load: bool = True,
        state_office: str = "ALL",
        status: str = "ALL",
        candidate_type: str = "State Candidates"
    ):
        """
        Initialize candidate lookup and automatically load all candidates.
        
        Args:
            auto_load: Whether to automatically download and load all candidates (default: True)
            state_office: State office filter for candidate download (default: 'ALL')
            status: Candidate status filter (default: 'ALL')
            candidate_type: Type of candidates (default: 'State Candidates')
        """
        # Primary storage: account number -> candidate data
        self.candidates: Dict[str, Dict[str, Any]] = {}
        
        # Index: normalized full name -> list of account numbers
        self.name_index: Dict[str, List[str]] = defaultdict(list)
        
        # Index: normalized last name -> list of account numbers
        self.lastname_index: Dict[str, List[str]] = defaultdict(list)
        
        # Index: (first, last) tuple -> list of account numbers
        self.component_index: Dict[Tuple[str, str], List[str]] = defaultdict(list)
        
        self.total_candidates = 0
        
        # Cache for lookups to avoid repeated searches for the same name
        self._lookup_cache: Dict[Tuple[str, Optional[str], bool, float], List[Dict[str, Any]]] = {}
        
        # Automatically load all candidates by default
        if auto_load:
            logger.info("Loading candidates from all available elections...")
            self.load_from_elections(
                election_ids=None,  # None means all elections
                state_office=state_office,
                status=status,
                candidate_type=candidate_type
            )
            logger.info(f"✓ Successfully loaded {self.total_candidates} total candidates")
    
    def _load_from_file(self, filepath: str) -> int:
        """
        Load candidate data from a CSV file (internal method).
        
        Args:
            filepath: Path to the candidate CSV file
            
        Returns:
            Number of candidates loaded
            
        Raises:
            IOError: If file cannot be read
            ValueError: If file format is invalid
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                if reader.fieldnames is None:
                    raise ValueError("CSV file has no headers")
                
                loaded = 0
                for row in reader:
                    acct_num = row.get('AcctNum', '').strip()
                    if not acct_num:
                        continue
                    
                    # Store candidate data
                    self.candidates[acct_num] = dict(row)
                    
                    # Build indexes
                    self._index_candidate(acct_num, row)
                    
                    loaded += 1
                
                self.total_candidates += loaded
                return loaded
                
        except IOError as e:
            logger.error(f"Failed to read candidate file {filepath}: {e}")
            raise IOError(f"Failed to read candidate file: {e}") from e
        except Exception as e:
            logger.error(f"Error loading candidates from {filepath}: {e}")
            raise ValueError(f"Invalid candidate file format: {e}") from e
    
    def load_from_elections(
        self,
        election_ids: Optional[List[str]] = None,
        state_office: str = "ALL",
        status: str = "ALL",
        candidate_type: str = "State Candidates"
    ) -> int:
        """
        Download and load candidates from one or more elections.
        
        Args:
            election_ids: List of election IDs to download. If None, downloads all available.
            state_office: State office filter. Default: 'ALL'
            status: Candidate status filter. Default: 'ALL'
            candidate_type: Type of candidates. Default: 'State Candidates'
            
        Returns:
            Total number of candidates loaded
            
        Raises:
            HTTPError: If download fails
        """
        from .candidate import CandidateScraper
        
        if election_ids is None:
            logger.info("Fetching list of available elections...")
            elections = CandidateScraper.get_available_elections()
            election_ids = [e['value'] for e in elections]
            logger.info(f"Found {len(election_ids)} elections to process")
        
        total_loaded = 0
        total_elections = len(election_ids)
        for idx, election_id in enumerate(election_ids, 1):
            logger.info(f"[{idx}/{total_elections}] Processing election: {election_id}")
            try:
                # Download to temp file
                temp_file = CandidateScraper.download(
                    election_year=election_id,
                    state_office=state_office,
                    status=status,
                    candidate_type=candidate_type
                )
                
                # Load from file
                loaded = self._load_from_file(temp_file)
                total_loaded += loaded
                logger.info(f"  ✓ Loaded {loaded} candidates from {election_id} (total: {total_loaded})")
                
                # Clean up temp file
                import os
                try:
                    os.remove(temp_file)
                except:
                    pass
                    
            except Exception as e:
                logger.warning(f"  ✗ Failed to load candidates for election {election_id}: {e}")
                continue
        
        logger.info(f"Completed loading candidates: {total_loaded} total from {total_elections} elections")
        return total_loaded
    
    def _index_candidate(self, acct_num: str, candidate: Dict[str, Any]) -> None:
        """
        Add a candidate to all indexes.
        
        Args:
            acct_num: Account number (key)
            candidate: Candidate data dictionary
        """
        # Build full name from components
        first = candidate.get('NameFirst', '').strip()
        last = candidate.get('NameLast', '').strip()
        middle = candidate.get('NameMiddle', '').strip()
        
        full_name = build_full_name(first, last, middle)
        normalized_full = normalize_name(full_name)
        
        # Index by normalized full name
        if normalized_full:
            self.name_index[normalized_full].append(acct_num)
        
        # Index by normalized last name
        normalized_last = normalize_name(last)
        if normalized_last:
            self.lastname_index[normalized_last].append(acct_num)
        
        # Index by (first, last) components
        normalized_first = normalize_name(first)
        if normalized_first and normalized_last:
            key = (normalized_first, normalized_last)
            self.component_index[key].append(acct_num)
    
    def find_by_name(
        self,
        name: str,
        party: Optional[str] = None,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Find candidates by name using exact and component matching strategies.
        
        Args:
            name: Name to search for (can be "Last, First" or "First Last" format)
            party: Optional party name for additional filtering/verification
            use_cache: Whether to use cached results for repeated lookups. Default: True
            
        Returns:
            List of matching candidate dictionaries, sorted by match confidence
        """
        if not name:
            return []
        
        normalized_search = normalize_name(name)
        if not normalized_search:
            return []
        
        # Check cache first
        if use_cache:
            cache_key = (normalized_search, party)
            if cache_key in self._lookup_cache:
                return self._lookup_cache[cache_key]
        
        matches = []
        seen_accounts = set()
        
        # Strategy 1: Exact match on normalized full name
        if normalized_search in self.name_index:
            for acct_num in self.name_index[normalized_search]:
                if acct_num not in seen_accounts:
                    candidate = self.candidates[acct_num]
                    if self._party_matches(candidate, party):
                        matches.append({
                            'candidate': candidate,
                            'match_method': 'exact',
                            'match_confidence': 1.0,
                            'account': acct_num
                        })
                        seen_accounts.add(acct_num)
        
        # Strategy 2: Component matching (first + last name)
        search_first, search_last, _ = parse_name_components(name)
        if search_first and search_last:
            normalized_first = normalize_name(search_first)
            normalized_last = normalize_name(search_last)
            key = (normalized_first, normalized_last)
            
            if key in self.component_index:
                for acct_num in self.component_index[key]:
                    if acct_num not in seen_accounts:
                        candidate = self.candidates[acct_num]
                        if self._party_matches(candidate, party):
                            matches.append({
                                'candidate': candidate,
                                'match_method': 'component',
                                'match_confidence': 0.95,
                                'account': acct_num
                            })
                            seen_accounts.add(acct_num)
        
        # Sort by confidence (highest first)
        matches.sort(key=lambda x: x['match_confidence'], reverse=True)
        
        # Cache the result
        if use_cache:
            cache_key = (normalized_search, party)
            self._lookup_cache[cache_key] = matches
        
        return matches
    
    def _party_matches(self, candidate: Dict[str, Any], party: Optional[str]) -> bool:
        """
        Check if candidate party matches the provided party.
        
        Args:
            candidate: Candidate data dictionary
            party: Party name to match (or None to skip party check)
            
        Returns:
            True if party matches or party is None
        """
        if party is None:
            return True
        
        candidate_party = candidate.get('PartyName', '').strip()
        candidate_party_code = candidate.get('PartyCode', '').strip()
        
        # Normalize party names for comparison
        party_lower = party.lower()
        candidate_party_lower = candidate_party.lower()
        
        # Check full party name
        if party_lower in candidate_party_lower or candidate_party_lower in party_lower:
            return True
        
        # Check party codes (DEM -> Democrat, REP -> Republican)
        party_code_map = {
            'democrat': 'DEM',
            'republican': 'REP',
            'dem': 'DEM',
            'rep': 'REP'
        }
        
        if party_lower in party_code_map:
            if candidate_party_code == party_code_map[party_lower]:
                return True
        
        return False
    
    def merge_with_transactions(
        self,
        transactions: List[Dict[str, Any]],
        name_field: str = 'recipient',
        party_field: Optional[str] = 'recipient_party',
        committee_lookup: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Merge candidate and committee information into transaction records.
        
        Args:
            transactions: List of transaction dictionaries
            name_field: Field name containing the candidate/recipient name. Default: 'recipient'
            party_field: Field name containing party information (optional). Default: 'recipient_party'
            committee_lookup: Optional CommitteeLookup instance to also check committees
            
        Returns:
            List of enriched transaction dictionaries with candidate/committee data added
        """
        total_transactions = len(transactions)
        if total_transactions == 0:
            return []
        
        logger.info(f"Enriching {total_transactions} transactions with candidate data...")
        
        # Pre-process: group transactions by name+party for batch processing
        # This allows us to cache lookups more effectively
        name_groups: Dict[Tuple[str, Optional[str]], List[int]] = {}
        empty_name_indices = []  # Track transactions with no name separately
        for idx, transaction in enumerate(transactions):
            name = transaction.get(name_field, '')
            party = transaction.get(party_field) if party_field else None
            if not name:
                empty_name_indices.append(idx)
            else:
                key = (name, party)
                if key not in name_groups:
                    name_groups[key] = []
                name_groups[key].append(idx)
        
        logger.info(f"  Found {len(name_groups)} unique recipient names (caching lookups for speed)")
        
        enriched = [None] * total_transactions  # Pre-allocate list
        matched_count = 0
        
        # Log progress for large datasets
        log_interval = max(1, total_transactions // 10)  # Log every 10% or at least every transaction
        processed_count = 0
        
        # Process by unique names (benefits from caching)
        for (name, party), indices in name_groups.items():
            # Find matching candidates first
            candidate_matches = []
            committee_matches = []
            if name:
                candidate_matches = self.find_by_name(
                    name=name,
                    party=party,
                    use_cache=True  # Use cache for repeated names
                )
                
                # If no candidate match and committee lookup is available, try committees
                if not candidate_matches and committee_lookup:
                    committee_matches = committee_lookup.find_by_name(
                        name=name,
                        use_cache=True,
                        fallback_search=True  # Enable online fallback for missing committees
                    )
            
            # Use candidate match if available, otherwise use committee match
            best_match = candidate_matches[0] if candidate_matches else (committee_matches[0] if committee_matches else None)
            entity = best_match.get('candidate') if candidate_matches else (best_match.get('committee') if committee_matches else None)
            entity_type = best_match.get('entity_type', 'candidate') if best_match else None
            
            if best_match:
                matched_count += len(indices)  # Count all transactions with this match
            
            # Enrich all transactions with this name+party
            for idx in indices:
                transaction = transactions[idx]
                enriched_transaction = dict(transaction)  # Create a copy
                
                if best_match and entity:
                    # Universal fields that work for both candidates and committees
                    enriched_transaction['entity_type'] = entity_type
                    enriched_transaction['entity_account'] = best_match['account']
                    
                    if entity_type == 'candidate':
                        # Candidate-specific fields
                        enriched_transaction['entity_name'] = build_full_name(
                            entity.get('NameFirst', ''),
                            entity.get('NameLast', ''),
                            entity.get('NameMiddle', '')
                        )
                        enriched_transaction['entity_name_first'] = entity.get('NameFirst', '')
                        enriched_transaction['entity_name_last'] = entity.get('NameLast', '')
                        enriched_transaction['entity_name_middle'] = entity.get('NameMiddle', '')
                        enriched_transaction['entity_election_id'] = entity.get('ElectionID', '')
                        enriched_transaction['entity_office'] = entity.get('OfficeDesc', '')
                        enriched_transaction['entity_status'] = entity.get('StatusDesc', '')
                        enriched_transaction['entity_party'] = entity.get('PartyName', '')
                        enriched_transaction['entity_email'] = entity.get('Email', '')
                        enriched_transaction['entity_phone'] = entity.get('Phone', '')
                        enriched_transaction['entity_type_detail'] = 'candidate'
                    else:
                        # Committee-specific fields
                        # Try to get committee name from various possible fields
                        committee_name = (
                            entity.get('Committee Name', '') or
                            entity.get('CommitteeName', '') or
                            entity.get('Name', '') or
                            entity.get('ComName', '')
                        )
                        enriched_transaction['entity_name'] = committee_name
                        enriched_transaction['entity_name_first'] = None
                        enriched_transaction['entity_name_last'] = None
                        enriched_transaction['entity_name_middle'] = None
                        enriched_transaction['entity_election_id'] = None
                        enriched_transaction['entity_office'] = None
                        enriched_transaction['entity_status'] = entity.get('Status', '') or entity.get('Committee Status', '')
                        enriched_transaction['entity_party'] = None
                        enriched_transaction['entity_email'] = None
                        enriched_transaction['entity_phone'] = None
                        enriched_transaction['entity_type_detail'] = entity.get('Type', '') or entity.get('Committee Type', '')
                else:
                    # No match found
                    enriched_transaction['entity_type'] = None
                    enriched_transaction['entity_account'] = None
                    enriched_transaction['entity_name'] = None
                    enriched_transaction['entity_name_first'] = None
                    enriched_transaction['entity_name_last'] = None
                    enriched_transaction['entity_name_middle'] = None
                    enriched_transaction['entity_election_id'] = None
                    enriched_transaction['entity_office'] = None
                    enriched_transaction['entity_status'] = None
                    enriched_transaction['entity_party'] = None
                    enriched_transaction['entity_email'] = None
                    enriched_transaction['entity_phone'] = None
                    enriched_transaction['entity_type_detail'] = None
                
                enriched[idx] = enriched_transaction
                processed_count += 1
                
                # Log progress periodically
                if processed_count % log_interval == 0 or processed_count == total_transactions:
                    progress_pct = (processed_count / total_transactions) * 100
                    logger.info(f"  Progress: {processed_count}/{total_transactions} ({progress_pct:.1f}%) - {matched_count} matched so far")
        
        # Handle transactions with no name
        for idx in empty_name_indices:
            transaction = transactions[idx]
            enriched_transaction = dict(transaction)
            enriched_transaction['entity_type'] = None
            enriched_transaction['entity_account'] = None
            enriched_transaction['entity_name'] = None
            enriched_transaction['entity_name_first'] = None
            enriched_transaction['entity_name_last'] = None
            enriched_transaction['entity_name_middle'] = None
            enriched_transaction['entity_election_id'] = None
            enriched_transaction['entity_office'] = None
            enriched_transaction['entity_status'] = None
            enriched_transaction['entity_party'] = None
            enriched_transaction['entity_email'] = None
            enriched_transaction['entity_phone'] = None
            enriched_transaction['entity_type_detail'] = None
            enriched[idx] = enriched_transaction
            processed_count += 1
        
        entity_type_str = "entities (candidates or committees)" if committee_lookup else "candidates"
        logger.info(f"✓ Enrichment complete: {matched_count}/{total_transactions} transactions matched to {entity_type_str} ({matched_count/total_transactions*100:.1f}%)")
        return enriched

