class Filter:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name

    def __and__(self, other: 'Filter' or str):
        return Filter(f"{self} && {other}") if isinstance(other, Filter) else Filter(f"{self} && {{{other}}}")

    def __or__(self, other: 'Filter' or str):
        return Filter(f"{self} || {other}") if isinstance(other, Filter) else Filter(f"{self} || {{{other}}}")

    def __invert__(self):
        return Filter(f"!{self}")

    def __eq__(self, other: 'Filter' or str):
        return Filter(f"{self} == {other}") if isinstance(other, Filter) else Filter(f"{self} == {{{other}}}")

    def __ne__(self, other: 'Filter' or str):
        return Filter(f"{self} !~ {other}") if isinstance(other, Filter) else Filter(f"{self} !~ {{{other}}}")

    def __lt__(self, other: 'Filter' or str):
        return Filter(f"{self} < {other}") if isinstance(other, (Filter, int)) else Filter(f"{self} < {{{other}}}")

    def __le__(self, other: 'Filter' or str):
        return Filter(f"{self} <= {other}") if isinstance(other, (Filter, int)) else Filter(f"{self} <= {{{other}}}")

    def __gt__(self, other: 'Filter' or str):
        return Filter(f"{self} > {other}") if isinstance(other, (Filter, int)) else Filter(f"{self} > {{{other}}}")

    def __ge__(self, other: 'Filter' or str):
        return Filter(f"{self} >= {other}") if isinstance(other, (Filter, int)) else Filter(f"{self} >= {{{other}}}")

    def match(self, pattern: str):
        if not isinstance(pattern, str):
            raise ValueError("filter_obj must be Filter instance")
        return f'{self} =~ "{pattern}"'

    def not_match(self, pattern: str):
        if not isinstance(pattern, str):
            raise ValueError("filter_obj must be Filter instance")
        return f'{self} !~ "{pattern}"'

