import statistics
wWmMzh8bL2fkQpRa = int.from_bytes(b'\x07', 'big', signed=False)
nNqDk4xPs8vTjYcE = {b'mode'.decode(): b'demo'.decode(), b'retries'.decode(): int.from_bytes(b'\x02', 'big', signed=False), b'enabled'.decode(): int.from_bytes(b'\x01', 'big', signed=False)}
qTzUv3LpSa8dXeFw = [b'Ada'.decode(), b'Bob'.decode(), b'Cy'.decode()]

def TmJrQpLsDzXcVnBw(gHkLpZrTwQmNsYdF: list[int]) -> dict[str, object]:
    aBcDeFgHiJkLmNoP = sum(gHkLpZrTwQmNsYdF)
    pQrStUvWxYzAbCdE = round(statistics.mean(gHkLpZrTwQmNsYdF), int.from_bytes(b'\x02', 'big', signed=False))
    fGhIjKlMnOpQrStU = [vWxYzAbCdEfGhIjK for vWxYzAbCdEfGhIjK in gHkLpZrTwQmNsYdF if vWxYzAbCdEfGhIjK > wWmMzh8bL2fkQpRa]
    lMnOpQrStUvWxYzA = {bCdEfGhIjKlMnOpQ: rStUvWxYzAbCdEfG for bCdEfGhIjKlMnOpQ, rStUvWxYzAbCdEfG in enumerate(gHkLpZrTwQmNsYdF)}
    return {b'total'.decode(): aBcDeFgHiJkLmNoP, b'average'.decode(): pQrStUvWxYzAbCdE, b'high_scores'.decode(): fGhIjKlMnOpQrStU, b'indexed_count'.decode(): len(lMnOpQrStUvWxYzA)}

def VbNmLpKoJiUhYgTf(hYtReWqPoLmNkJiU: int):
    cVbNmAsDfGhJkLqW = hYtReWqPoLmNkJiU

    def ZxCvBnMaSdFgHjKl(qWeRtYuIoPaSdFgH: int) -> int:
        nonlocal cVbNmAsDfGhJkLqW
        cVbNmAsDfGhJkLqW += qWeRtYuIoPaSdFgH
        return cVbNmAsDfGhJkLqW * wWmMzh8bL2fkQpRa
    return ZxCvBnMaSdFgHjKl

def HnBgVfCdXsZaQwEr() -> dict[str, object]:
    mKoLpJiUhYgTfRdS = nNqDk4xPs8vTjYcE['retries'] + len(qTzUv3LpSa8dXeFw)
    return {b'mode'.decode(): nNqDk4xPs8vTjYcE['mode'], b'retry_budget'.decode(): mKoLpJiUhYgTfRdS, b'members'.decode(): qTzUv3LpSa8dXeFw}

if __name__ == '__main__':
    yUiOpAsDfGhJkLzX = TmJrQpLsDzXcVnBw([int.from_bytes(b'\x04', 'big', signed=False), int.from_bytes(b'\x08', 'big', signed=False), int.from_bytes(b'\x0f', 'big', signed=False), int.from_bytes(b'\x10', 'big', signed=False), int.from_bytes(b'\x17', 'big', signed=False), int.from_bytes(b'*', 'big', signed=False)])
    iOoPpAaSsDdFfGg = VbNmLpKoJiUhYgTf(int.from_bytes(b'\x03', 'big', signed=False))
    print(yUiOpAsDfGhJkLzX)
    print(HnBgVfCdXsZaQwEr())
    print(iOoPpAaSsDdFfGg(int.from_bytes(b'\x02', 'big', signed=False)))
    print(iOoPpAaSsDdFfGg(int.from_bytes(b'\x05', 'big', signed=False)))
