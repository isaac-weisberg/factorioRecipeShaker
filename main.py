from copy import deepcopy
from array import array
from dataclasses import dataclass
from ppprint import ppprint
from pprint import pprint
from math import gcd

def decimal(whole: int, fraction: int = 0) -> Precise:
    base = 10
    while fraction >= base:
        base = base * 10

    return Precise(whole * base + fraction, base).simplified()

@dataclass
class Precise:
    top: int
    bottom: int = 1

    def isFraction(self) -> bool:
        return self.bottom != 1

    def simplified(self) -> Precise:
        divisor = gcd(self.top, self.bottom)
        if divisor == 1:
            return self

        return Precise(self.top // divisor, self.bottom // divisor)

    def mul(self, rhs: Precise) -> Precise:
        if self.isFraction() == rhs.isFraction() and not self.isFraction():
            return Precise(self.top * rhs.top)
        return Precise(self.top * rhs.top, self.bottom * rhs.bottom).simplified()

    def div(self, rhs: Precise) -> Precise:
        return self.mul(Precise(rhs.bottom, rhs.top)).simplified()

    def decimalish(self) -> str:
        if self.isFraction():
            return "{}/{} ({:.2f})".format(self.top, self.bottom, self.top / self.bottom)
        else:
            return "{}".format(self.top)

@dataclass
class RecipeSource:
    material: str
    count: int

@dataclass
class Recipe:
    sources: list[RecipeSource]
    time: Precise
    output: RecipeSource

@dataclass
class PragmaDeclaration:
    material: str
    qualifier: str

def getRecipes() -> tuple[list[Recipe], list[PragmaDeclaration]]:
    def parseTime(s: str) -> Precise:
        secondsString = entry.split('s')[0]
        if '.' in secondsString:
            parts = secondsString.split('.')
            whole = int(parts[0])
            fraction = int(parts[1])
            time = decimal(whole, fraction)
        else:
            whole = int(secondsString)
            time = Precise(whole)

        return time

    def parseRecipeSource(s: str) -> RecipeSource:
        parts = s.split(" ")
        countString = parts[0]
        count = int(countString)
        name = " ".join(parts[1:])

        return RecipeSource(name, count)

    def parsePragma(s: str) -> PragmaDeclaration|None:
        parts = s.split('=')
        if len(parts) == 1:
            return None
        return PragmaDeclaration(parts[0], parts[1])

    filePath = 'recipes.txt'

    with open(filePath, 'r') as file:
        file_content = file.read()

    lines = file_content.splitlines()

    recipes: list[Recipe] = []
    pragmas: list[PragmaDeclaration] = []
    masterStage = 0

    for line in lines:
        entries = line.split(", ")

        match masterStage:
            case 0:
                if line.startswith('[RECIPES]'):
                    masterStage = 1
                    continue
                
                pragma = parsePragma(line)
                if pragma:
                    pragmas.append(pragma)
            case 1:
                stage = 0
                
                sources: list[RecipeSource] = []
                time: Precise | None = None
                output: RecipeSource | None = None
                for entry in entries:
                    if stage == 0:
                        if entry[-1] == 's' and entry[-2].isdigit():
                            stage = 1

                            time = parseTime(entry)
                        else:
                            recipe = parseRecipeSource(entry)
                            sources.append(recipe)
                    else:
                        output = parseRecipeSource(entry)

                if len(sources) == 0:
                    raise RuntimeError('no sources {}'.format(line))

                if time == None:
                    raise RuntimeError('no time {}'.format(line))
                
                if output == None:
                    raise RuntimeError('no output {}'.format(output))
                
                recipe = Recipe(sources, time, output)
                recipes.append(recipe)

    return (recipes, pragmas)


def buildRecipesLookupTable(recipes: list[Recipe]) -> dict[str, Recipe]:
    result: dict['str', Recipe] = {}

    for recipe in recipes:
        result[recipe.output.material] = recipe

    return result

def buildKnownToHaveNoRecipeSet(pragmas: list[PragmaDeclaration]) -> set[str]:
    result: set[str] = set()
    for pragma in pragmas:
        if pragma.qualifier == 'N/R':
            result.add(pragma.material)

    return result

def buildFurnaceRecipes(pragmas: list[PragmaDeclaration]) -> set[str]:
    result: set[str] = set()
    for pragma in pragmas:
        if pragma.qualifier == 'furnace':
            result.add(pragma.material)

    return result

def buildChemicalPlantRecipes(pragmas: list[PragmaDeclaration]) -> set[str]:
    result: set[str] = set()
    for pragma in pragmas:
        if pragma.qualifier == 'chemical plant':
            result.add(pragma.material)

    return result

@dataclass
class RecipeBook:
    recipes: list[Recipe]
    pragmas: list[PragmaDeclaration]
    recipesLookupTable: dict[str, Recipe]
    knownToHaveNoRecipeSet: set[str]
    furnaceRecipeSet: set[str]
    chemicalPlantRecipes: set[str]

    def __init__(self, recipes: list[Recipe], pragmas: list[PragmaDeclaration]):
        self.recipes= recipes
        self.pragmas = pragmas

        self.recipesLookupTable = buildRecipesLookupTable(recipes)
        self.knownToHaveNoRecipeSet = buildKnownToHaveNoRecipeSet(pragmas)
        self.furnaceRecipeSet = buildFurnaceRecipes(pragmas)
        self.chemicalPlantRecipes = buildChemicalPlantRecipes(pragmas)

@dataclass
class Productivity:
    assemblers: Precise
    furnaces: Precise

@dataclass
class Environment:
    recipeBook: RecipeBook
    productivity: Productivity

    def getTimeMultiplier(self, material: str) -> Precise:
        if material in self.recipeBook.chemicalPlantRecipes:
            return Precise(1)

        if material in self.recipeBook.furnaceRecipeSet:
            return self.productivity.furnaces

        # assuming it's assembler
        return self.productivity.assemblers

@dataclass
class RequirementTreeNode:
    pipelines: Precise
    materialName: str
    dependencies: list[RequirementTreeNode]

def assembleRequirementTree(environment: Environment, material: str, count: Precise, time: Precise) -> RequirementTreeNode:
    recipe = environment.recipeBook.recipesLookupTable[material]

    timeMultiplier = environment.getTimeMultiplier(recipe.output.material)
    realRecipeTime = recipe.time.div(timeMultiplier)

    # How many pipelines to get 1 pipeline worth every "time" period 
    onePipelineInTime = realRecipeTime.div(time)

    # How many pipelines to achieve the count
    pipelinesToAchieveCount = count.div(Precise(recipe.output.count))

    pipelinesNeeded = onePipelineInTime.mul(pipelinesToAchieveCount)

    dependencies: list[RequirementTreeNode] = []
    for source in recipe.sources:
        # How many items of this source I need
        totalNeed = Precise(source.count).mul(pipelinesNeeded)

        if source.material in environment.recipeBook.recipesLookupTable:
            dependencyNone = assembleRequirementTree(environment, source.material, totalNeed, realRecipeTime)
            dependencies.append(dependencyNone)
        else:
            if source.material in environment.recipeBook.knownToHaveNoRecipeSet:
                dependencies.append(RequirementTreeNode(totalNeed, source.material, []))
            else:
                dependencies.append(RequirementTreeNode(totalNeed, '{} NO RECIPE'.format(source.material), []))

    return RequirementTreeNode(pipelinesNeeded, recipe.output.material, dependencies)

def formatRequirementTree(tree: RequirementTreeNode) -> str:
    lines: list[str] = []

    def flush(tree: RequirementTreeNode, i: int):
        indentation = "    " * i
        rootLine = "{}{} {}".format(indentation, tree.pipelines.decimalish(), tree.materialName)
        lines.append(rootLine)
        for dep in tree.dependencies:
            flush(dep, i + 1)
        
    i = 0
    flush(tree, i)

    return "\r\n".join(lines)

def simplifyTree(tree: RequirementTreeNode) -> tuple[RequirementTreeNode, str]:
    quantities: list[int] = []
    thereIsAFraction = False

    def flushQuantityOfDerivedNodes(tree: RequirementTreeNode):
        nonlocal thereIsAFraction
        if not tree.dependencies:
            return

        if tree.pipelines.isFraction():
            thereIsAFraction = True
            return

        quantities.append(tree.pipelines.top)
        for dep in tree.dependencies:
            if thereIsAFraction:
                break

            flushQuantityOfDerivedNodes(dep)

    flushQuantityOfDerivedNodes(tree)

    if not quantities:
        return (tree, 'no quantities')

    if thereIsAFraction:
        return (tree, 'there is a fraction')

    divisor = gcd(*quantities)

    if divisor == 1:
        return (tree, 'doesnt get simpler')

    result = deepcopy(tree)

    def divideQuantitiesByDivisor(tree: RequirementTreeNode, divisor: int):
        tree.pipelines = tree.pipelines.div(Precise(divisor))
        for dep in tree.dependencies:
            divideQuantitiesByDivisor(dep, divisor)

    divideQuantitiesByDivisor(result, divisor)

    return (result, 'simplified with divisor {}'.format(divisor))

def main():
    recipes, pragmas = getRecipes()

    recipeBook = RecipeBook(recipes, pragmas)
    productivity = Productivity(decimal(1, 0), Precise(2))

    environment = Environment(recipeBook, productivity)

    tree = assembleRequirementTree(environment, 'red splitter', decimal(1), decimal(2, 0))
    formatted = formatRequirementTree(tree)
    # tree, result = simplifyTree(tree)
    # print("Simplify result {}".format(result))
    ppprint(productivity)
    print(formatted)

main()