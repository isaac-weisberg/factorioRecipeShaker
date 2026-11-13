from copy import deepcopy
from array import array
from dataclasses import dataclass
from ppprint import ppprint
from pprint import pprint

def simplify(top: int, bottom: int, against: int) -> tuple[bool, int, int]:
    if top % against == 0 and bottom % against == 0:
        return (True, top // against, bottom // against)

    return (False, top, bottom)

def decimal(whole: int, fraction: int) -> Precise:
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
        if not self.isFraction():
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

        return result

    def mul(self, rhs: Precise) -> Precise:
        if self.isFraction() == rhs.isFraction() and self.isFraction():
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

def getRecipes() -> list[Recipe]:
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

    filePath = 'recipes.txt'

    with open(filePath, 'r') as file:
        file_content = file.read()

    lines = file_content.splitlines()

    recipes: list[Recipe] = []

    for line in lines:
        entries = line.split(", ")

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

    return recipes


def buildRecipesLookupTable(recipes: list[Recipe]) -> dict['str', Recipe]:
    result: dict['str', Recipe] = {}

    for recipe in recipes:
        result[recipe.output.material] = recipe

    return result

recipes = getRecipes()

recipesLookupTable = buildRecipesLookupTable(recipes)


@dataclass
class RequirementTreeNode:
    pipelines: Precise
    materialName: str
    dependencies: list[RequirementTreeNode]

def assembleRequirementTree(recipe: Recipe, count: Precise, time: Precise) -> RequirementTreeNode:
    debug = recipe.output.material == "purple science"

    # How many pipelines to get 1 pipeline worth every "time" period 
    onePipelineInTime = recipe.time.div(time)

    # How many pipelines to achieve the count
    pipelinesToAchieveCount = count.div(Precise(recipe.output.count))

    pipelinesNeeded = onePipelineInTime.mul(pipelinesToAchieveCount)

    if debug:
        ppprint(time)
        ppprint(count)
        ppprint(recipe.time)
        ppprint(Precise(recipe.output.count))
        ppprint(onePipelineInTime)
        ppprint(pipelinesToAchieveCount)
        ppprint(pipelinesNeeded)


    dependencies: list[RequirementTreeNode] = []
    for source in recipe.sources:
        # How many items of this source I need
        totalNeed = Precise(source.count).mul(pipelinesNeeded)
        dependencyRecipe = recipesLookupTable.get(source.material)
        if dependencyRecipe != None:
            dependencyNone = assembleRequirementTree(dependencyRecipe, totalNeed, recipe.time)
            dependencies.append(dependencyNone)
        else:
            dependencies.append(RequirementTreeNode(totalNeed, '{} (N/R)'.format(source.material), []))


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

print(formatRequirementTree(assembleRequirementTree(recipesLookupTable['purple science'], Precise(3), decimal(0, 5))))