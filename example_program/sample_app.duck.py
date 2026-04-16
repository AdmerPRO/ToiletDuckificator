import math
BK5s6uA9cpV5XjAP = 4

def greet_user(JIQBvG8taQVHOmle: str) -> str:
    UIxlt8fAIWlS2BMx = f'Hello, {JIQBvG8taQVHOmle}!'
    return UIxlt8fAIWlS2BMx

def compute_circle(YXslsWmWgt8gCLeY: float) -> float:
    zuBM_fWVTMKYstlc = math.pi * YXslsWmWgt8gCLeY * YXslsWmWgt8gCLeY
    return zuBM_fWVTMKYstlc + BK5s6uA9cpV5XjAP

def build_summary(bRDxwFFoUUYx7auh: list[int]) -> dict[str, int]:
    eSNsfYfpsAAhDO9s = sum(bRDxwFFoUUYx7auh)
    FuFm2n0pOCBBXbeW = max(bRDxwFFoUUYx7auh)
    DKfuhtaMhFKyhXpv = {W6E0bOfcpe3d1zXj: H06VbGVDvVU55LFd for W6E0bOfcpe3d1zXj, H06VbGVDvVU55LFd in enumerate(bRDxwFFoUUYx7auh)}
    return {'total': eSNsfYfpsAAhDO9s, 'largest': FuFm2n0pOCBBXbeW, 'indexed': len(DKfuhtaMhFKyhXpv)}

def make_counter(P4tZJZyTP9OHFbEb: int):
    kK3UzA6FGO0Ebjha = P4tZJZyTP9OHFbEb

    def inner(oFhpclMDGHmRURDh: int) -> int:
        nonlocal kK3UzA6FGO0Ebjha
        kK3UzA6FGO0Ebjha += oFhpclMDGHmRURDh
        return kK3UzA6FGO0Ebjha
    return inner
if __name__ == '__main__':
    print(greet_user('Toilet Duck'))
    print(round(compute_circle(3.5), 2))
    print(build_summary([3, 5, 8, 13]))
    HVtIaPpPRIDBae9j = make_counter(10)
    print(HVtIaPpPRIDBae9j(2))
    print(HVtIaPpPRIDBae9j(7))
