from dataclasses import dataclass

@dataclass
class CompanySearchResult:
    company_name: str
    company_url: str
    rank: int
