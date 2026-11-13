from copy import deepcopy
from array import array

def simplify(top: int, bottom: int, against: int) -> tuple[bool, int, int]:
    if top % against == 0 and bottom % against == 0:
        return (True, top // against, bottom // against)

    return (False, top, bottom)

def decimal(whole: int, fraction: int) -> Precise:
    base = 10
    while fraction >= base:
        base = base * 10

    return Precise(True, whole * base + fraction, base).simplified()

class Precise:
    fraction: bool
    top: int
    bottom: int

    def __init__(self, fraction, top, bottom = 1):
        self.fraction = fraction
        self.top = top
        self.bottom = bottom

    def simplified(self) -> Precise:
        if not self.fraction:
            return self
        result = deepcopy(self)
        for against in [7, 5, 3, 2]:
            simplified = True
            while simplified:
                simple = simplify(result.top, result.bottom, against)
                simplified = simple[0]
                if simplified:
                    result.top = simple[1]
                    result.bottom = simple[2]

        if result.bottom == 1:
            result.fraction = False

        return result

    def mul(self, rhs: Precise) -> Precise:
        if self.fraction == rhs.fraction and self.fraction:
            return Precise(False, self.top * rhs.top)
        return Precise(True, self.top * rhs.top, self.bottom * rhs.bottom).simplified()

    def div(self, rhs: Precise) -> Precise:
        return self.mul(Precise(True, rhs.bottom, rhs.top)).simplified()

    def decimalish(self) -> str:
        if self.fraction:
            return "{}/{} ({:.2f})".format(self.top, self.bottom, self.top / self.bottom)
        else:
            return "{}".format(self.top)

class RecipeSource:
    material: str
    count: int

    def __init__(self, material: str, count: int):
        self.material = material
        self.count = count

class Recipe:
    sources: list[RecipeSource]
    time: Precise
    output: RecipeSource

    def __init__(self, sources: list[RecipeSource], time: Precise, output: RecipeSource):
        self.sources = sources
        self.time = time
        self.output = output

recipes = [
    Recipe([RecipeSource('stone', 2)], decimal(3, 2), RecipeSource('brick', 1)),
    Recipe([RecipeSource('iron', 1)], decimal(0, 5), RecipeSource('stick', 2)),
]
