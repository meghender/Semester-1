#include <iostream>
#include <fstream>
#include <vector>
#include <map>
#include <set>
#include <queue>
#include <algorithm>
#include <cstdlib>

// Coordinate representation
struct Coord {
    int x, y;
    bool operator==(const Coord& o) const { return x == o.x && y == o.y; }
    bool operator!=(const Coord& o) const { return !(*this == o); }
    bool operator<(const Coord& o) const { return x != o.x ? x < o.x : y < o.y; }
};

// Metro route specification
struct Route {
    int lineNum;
    Coord origin, destination;
};

// Configuration parameters
struct Config {
    int gridWidth, gridHeight, routeCount, maxBends;
    int scenarioType, hotspotCount;
    std::vector<Route> routes;
    std::vector<Coord> hotspots;
};

// Clause management
class ClauseManager {
    std::vector<std::vector<int>> allClauses;
    
public:
    void insert(const std::vector<int>& c) {
        if (!c.empty()) allClauses.push_back(c);
    }
    
    void insertPairwiseExclusion(const std::vector<int>& vars, int guard = 0) {
        for (size_t a = 0; a < vars.size(); ++a) {
            for (size_t b = a + 1; b < vars.size(); ++b) {
                if (guard == 0) {
                    insert({-vars[a], -vars[b]});
                } else {
                    insert({-guard, -vars[a], -vars[b]});
                }
            }
        }
    }
    
    size_t count() const { return allClauses.size(); }
    
    const std::vector<std::vector<int>>& getClauses() const { return allClauses; }
};

// === SCENARIO A (Simple Grid Model) ===
namespace ScenarioA {
    int nextVarId = 1;
    std::map<std::vector<int>, int> symbolTable;
    
    // Symbol types
    enum SymType { SYM_OCCUPIED = 1, SYM_NORTH = 2, SYM_SOUTH = 3, SYM_WEST = 4, SYM_EAST = 5, 
                   SYM_BEND = 6, SYM_BEND_COUNT = 7, SYM_GUIDE = 8 };
    
    int fetchVariable(const std::vector<int>& signature) {
        if (symbolTable.find(signature) == symbolTable.end()) {
            symbolTable[signature] = nextVarId++;
        }
        return symbolTable[signature];
    }
    
    void enforceExactlyOne(ClauseManager& cm, const std::vector<int>& vars, int condition = 0) {
        if (vars.empty()) {
            if (condition != 0) cm.insert({-condition});
            return;
        }
        if (condition == 0) {
            cm.insert(vars);
        } else {
            std::vector<int> guarded = vars;
            guarded.insert(guarded.begin(), -condition);
            cm.insert(guarded);
        }
        cm.insertPairwiseExclusion(vars, condition);
    }
    
    int computeManhattan(Coord a, Coord b) {
        return abs(a.x - b.x) + abs(a.y - b.y);
    }
    
    // Pathfinding node for heuristic generation
    struct PathNode {
        Coord location;
        int bendsSoFar;
        int costFromStart;
        Coord predecessor;
        char arrivalMove;
        int totalCost;
        bool operator>(const PathNode& o) const { return totalCost > o.totalCost; }
    };
    
    std::vector<Coord> constructPathAStar(Coord src, Coord dst, const std::vector<std::vector<bool>>& occupied, 
                                           int gridW, int gridH, int bendLimit) {
        std::priority_queue<PathNode, std::vector<PathNode>, std::greater<PathNode>> frontier;
        std::map<Coord, PathNode> explored;
        
        PathNode initial = {src, 0, 0, src, 'X', computeManhattan(src, dst)};
        frontier.push(initial);
        explored[src] = initial;
        
        int deltaX[] = {0, 0, -1, 1};
        int deltaY[] = {-1, 1, 0, 0};
        char dirChars[] = {'N', 'S', 'W', 'E'};
        
        while (!frontier.empty()) {
            PathNode curr = frontier.top();
            frontier.pop();
            
            if (curr.location == dst) {
                std::vector<Coord> reconstructed;
                Coord trace = dst;
                while (!(trace == src)) {
                    reconstructed.push_back(trace);
                    trace = explored[trace].predecessor;
                }
                reconstructed.push_back(src);
                std::reverse(reconstructed.begin(), reconstructed.end());
                return reconstructed;
            }
            
            for (int d = 0; d < 4; ++d) {
                Coord adj = {curr.location.x + deltaX[d], curr.location.y + deltaY[d]};
                if (adj.x < 0 || adj.x >= gridW || adj.y < 0 || adj.y >= gridH) continue;
                if (occupied[adj.y][adj.x] && !(adj == dst)) continue;
                
                int updatedBends = curr.bendsSoFar;
                if (curr.arrivalMove != 'X' && dirChars[d] != curr.arrivalMove) {
                    bool prevVertical = (curr.arrivalMove == 'N' || curr.arrivalMove == 'S');
                    bool currVertical = (dirChars[d] == 'N' || dirChars[d] == 'S');
                    if (prevVertical != currVertical) updatedBends++;
                }
                if (updatedBends > bendLimit) continue;
                
                int updatedCost = curr.costFromStart + 1;
                if (explored.find(adj) == explored.end() || updatedCost < explored[adj].costFromStart) {
                    int heuristic = computeManhattan(adj, dst);
                    PathNode successor = {adj, updatedBends, updatedCost, curr.location, dirChars[d], updatedCost + heuristic};
                    explored[adj] = successor;
                    frontier.push(successor);
                }
            }
        }
        return {};
    }
    
    void generateConstraints(const Config& cfg, ClauseManager& cm) {
        // Attempt greedy solution
        bool greedyFound = false;
        std::map<int, std::vector<Coord>> greedyPaths;
        std::vector<Route> sortedRoutes = cfg.routes;
        std::sort(sortedRoutes.begin(), sortedRoutes.end(), [](const Route& a, const Route& b) {
            return computeManhattan(a.origin, a.destination) > computeManhattan(b.origin, b.destination);
        });
        
        std::vector<std::vector<bool>> blocked(cfg.gridHeight, std::vector<bool>(cfg.gridWidth, false));
        greedyFound = true;
        for (const auto& rt : sortedRoutes) {
            std::vector<Coord> trajectory = constructPathAStar(rt.origin, rt.destination, blocked, 
                                                                cfg.gridWidth, cfg.gridHeight, cfg.maxBends);
            if (trajectory.empty()) {
                greedyFound = false;
                break;
            }
            greedyPaths[rt.lineNum] = trajectory;
            for (const auto& cell : trajectory) blocked[cell.y][cell.x] = true;
        }
        
        // Generate SAT constraints
        for (const auto& rt : cfg.routes) {
            for (int row = 0; row < cfg.gridHeight; ++row) {
                for (int col = 0; col < cfg.gridWidth; ++col) {
                    Coord pos = {col, row};
                    int occupiedVar = fetchVariable({SYM_OCCUPIED, rt.lineNum, row, col});
                    
                    std::vector<int> incomingMoves, outgoingMoves;
                    if (row > 0) {
                        incomingMoves.push_back(fetchVariable({SYM_SOUTH, rt.lineNum, row - 1, col}));
                        outgoingMoves.push_back(fetchVariable({SYM_NORTH, rt.lineNum, row, col}));
                    }
                    if (row < cfg.gridHeight - 1) {
                        incomingMoves.push_back(fetchVariable({SYM_NORTH, rt.lineNum, row + 1, col}));
                        outgoingMoves.push_back(fetchVariable({SYM_SOUTH, rt.lineNum, row, col}));
                    }
                    if (col > 0) {
                        incomingMoves.push_back(fetchVariable({SYM_EAST, rt.lineNum, row, col - 1}));
                        outgoingMoves.push_back(fetchVariable({SYM_WEST, rt.lineNum, row, col}));
                    }
                    if (col < cfg.gridWidth - 1) {
                        incomingMoves.push_back(fetchVariable({SYM_WEST, rt.lineNum, row, col + 1}));
                        outgoingMoves.push_back(fetchVariable({SYM_EAST, rt.lineNum, row, col}));
                    }
                    
                    std::vector<int> allDirections = incomingMoves;
                    allDirections.insert(allDirections.end(), outgoingMoves.begin(), outgoingMoves.end());
                    
                    for (int dir : allDirections) cm.insert({-dir, occupiedVar});
                    
                    std::vector<int> occupiedImplies = {-occupiedVar};
                    occupiedImplies.insert(occupiedImplies.end(), allDirections.begin(), allDirections.end());
                    cm.insert(occupiedImplies);
                    
                    if (pos == rt.origin) {
                        cm.insert({occupiedVar});
                        enforceExactlyOne(cm, outgoingMoves);
                        for (int v : incomingMoves) cm.insert({-v});
                    } else if (pos == rt.destination) {
                        cm.insert({occupiedVar});
                        enforceExactlyOne(cm, incomingMoves);
                        for (int v : outgoingMoves) cm.insert({-v});
                    } else {
                        enforceExactlyOne(cm, incomingMoves, occupiedVar);
                        enforceExactlyOne(cm, outgoingMoves, occupiedVar);
                        for (int v : allDirections) cm.insert({occupiedVar, -v});
                    }
                }
            }
            
            // Bend constraints
            for (int row = 0; row < cfg.gridHeight; ++row) {
                for (int col = 0; col < cfg.gridWidth; ++col) {
                    Coord pos = {col, row};
                    if (pos == rt.origin || pos == rt.destination) continue;
                    
                    int bendVar = fetchVariable({SYM_BEND, rt.lineNum, row, col});
                    
                    int fromN = (row < cfg.gridHeight - 1) ? fetchVariable({SYM_NORTH, rt.lineNum, row + 1, col}) : 0;
                    int fromS = (row > 0) ? fetchVariable({SYM_SOUTH, rt.lineNum, row - 1, col}) : 0;
                    int fromW = (col < cfg.gridWidth - 1) ? fetchVariable({SYM_WEST, rt.lineNum, row, col + 1}) : 0;
                    int fromE = (col > 0) ? fetchVariable({SYM_EAST, rt.lineNum, row, col - 1}) : 0;
                    
                    int toN = (row > 0) ? fetchVariable({SYM_NORTH, rt.lineNum, row, col}) : 0;
                    int toS = (row < cfg.gridHeight - 1) ? fetchVariable({SYM_SOUTH, rt.lineNum, row, col}) : 0;
                    int toW = (col > 0) ? fetchVariable({SYM_WEST, rt.lineNum, row, col}) : 0;
                    int toE = (col < cfg.gridWidth - 1) ? fetchVariable({SYM_EAST, rt.lineNum, row, col}) : 0;
                    
                    std::vector<int> hIn = {fromW, fromE}, vIn = {fromN, fromS};
                    std::vector<int> hOut = {toW, toE}, vOut = {toN, toS};
                    
                    for (int hi : hIn) if (hi) for (int vo : vOut) if (vo) cm.insert({-hi, -vo, bendVar});
                    for (int vi : vIn) if (vi) for (int ho : hOut) if (ho) cm.insert({-vi, -ho, bendVar});
                }
            }
            
            // Bend counting
            int totalCells = cfg.gridWidth * cfg.gridHeight;
            for (int cellIdx = 0; cellIdx < totalCells; ++cellIdx) {
                int r = cellIdx / cfg.gridWidth, c = cellIdx % cfg.gridWidth;
                int bendHere = fetchVariable({SYM_BEND, rt.lineNum, r, c});
                
                for (int bendNum = 1; bendNum <= cfg.maxBends + 1; ++bendNum) {
                    int counterVar = fetchVariable({SYM_BEND_COUNT, rt.lineNum, cellIdx, bendNum});
                    
                    if (cellIdx == 0) {
                        cm.insert({-bendHere, counterVar});
                        if (bendNum > 1) cm.insert({-counterVar});
                    } else {
                        int prevSame = fetchVariable({SYM_BEND_COUNT, rt.lineNum, cellIdx - 1, bendNum});
                        int prevLess = (bendNum > 1) ? fetchVariable({SYM_BEND_COUNT, rt.lineNum, cellIdx - 1, bendNum - 1}) : 0;
                        
                        cm.insert({-prevSame, counterVar});
                        if (prevLess) cm.insert({-prevLess, -bendHere, counterVar});
                        else cm.insert({-bendHere, counterVar});
                    }
                }
            }
            cm.insert({-fetchVariable({SYM_BEND_COUNT, rt.lineNum, totalCells - 1, cfg.maxBends + 1})});
        }
        
        // Cell exclusivity
        for (int row = 0; row < cfg.gridHeight; ++row) {
            for (int col = 0; col < cfg.gridWidth; ++col) {
                std::vector<int> occupants;
                for (int k = 0; k < cfg.routeCount; ++k) {
                    occupants.push_back(fetchVariable({SYM_OCCUPIED, k, row, col}));
                }
                cm.insertPairwiseExclusion(occupants);
            }
        }
        
        // Greedy hints
        if (greedyFound) {
            for (const auto& rt : cfg.routes) {
                if (greedyPaths.count(rt.lineNum)) {
                    int hintVar = fetchVariable({SYM_GUIDE, rt.lineNum});
                    for (const auto& cell : greedyPaths[rt.lineNum]) {
                        cm.insert({-fetchVariable({SYM_OCCUPIED, rt.lineNum, cell.y, cell.x}), hintVar});
                    }
                }
            }
        }
    }
}

// === SCENARIO B (State-Space Model) ===
namespace ScenarioB {
    int stateVarTotal;
    int baseVarId;
    
    // Directions: 0=N, 1=S, 2=E, 3=W, 4=START
    const int dx[] = {0, 0, 1, -1};
    const int dy[] = {-1, 1, 0, 0};
    const int reverseDir[] = {1, 0, 3, 2};
    
    int computeStateVar(int route, int col, int row, int direction, int bends, int gridW, int gridH, int bendLimit) {
        return 1 + bends + direction * (bendLimit + 1) + 
               row * (bendLimit + 1) * 5 + 
               col * (bendLimit + 1) * 5 * gridH + 
               route * (bendLimit + 1) * 5 * gridH * gridW;
    }
    
    int computeCellVar(int route, int col, int row, int gridW, int gridH) {
        return stateVarTotal + 1 + route * (gridW * gridH) + row * gridW + col;
    }
    
    void generateConstraints(const Config& cfg, ClauseManager& cm) {
        stateVarTotal = cfg.routeCount * cfg.gridWidth * cfg.gridHeight * 5 * (cfg.maxBends + 1);
        int totalVars = stateVarTotal + (cfg.routeCount * cfg.gridWidth * cfg.gridHeight);
        baseVarId = totalVars + 1;
        
        for (int route = 0; route < cfg.routeCount; ++route) {
            int srcX = cfg.routes[route].origin.x, srcY = cfg.routes[route].origin.y;
            int dstX = cfg.routes[route].destination.x, dstY = cfg.routes[route].destination.y;
            
            cm.insert({computeStateVar(route, srcX, srcY, 4, 0, cfg.gridWidth, cfg.gridHeight, cfg.maxBends)});
            cm.insert({computeCellVar(route, dstX, dstY, cfg.gridWidth, cfg.gridHeight)});
            
            for (int row = 0; row < cfg.gridHeight; ++row) {
                for (int col = 0; col < cfg.gridWidth; ++col) {
                    for (int bends = 0; bends <= cfg.maxBends; ++bends) {
                        for (int arrivalDir = 0; arrivalDir < 5; ++arrivalDir) {
                            int currentState = computeStateVar(route, col, row, arrivalDir, bends, 
                                                                 cfg.gridWidth, cfg.gridHeight, cfg.maxBends);
                            
                            if (col == dstX && row == dstY) continue;
                            
                            std::vector<int> transitions;
                            
                            if (arrivalDir == 4) {
                                for (int moveDir = 0; moveDir < 4; ++moveDir) {
                                    int nx = col + dx[moveDir], ny = row + dy[moveDir];
                                    if (nx >= 0 && nx < cfg.gridWidth && ny >= 0 && ny < cfg.gridHeight) {
                                        transitions.push_back(computeStateVar(route, nx, ny, reverseDir[moveDir], 0, 
                                                                               cfg.gridWidth, cfg.gridHeight, cfg.maxBends));
                                    }
                                }
                            } else {
                                int straightDir = reverseDir[arrivalDir];
                                int nx = col + dx[straightDir], ny = row + dy[straightDir];
                                if (nx >= 0 && nx < cfg.gridWidth && ny >= 0 && ny < cfg.gridHeight) {
                                    transitions.push_back(computeStateVar(route, nx, ny, arrivalDir, bends, 
                                                                           cfg.gridWidth, cfg.gridHeight, cfg.maxBends));
                                }
                                
                                if (bends < cfg.maxBends) {
                                    for (int turnDir = 0; turnDir < 4; ++turnDir) {
                                        if (turnDir == straightDir || turnDir == arrivalDir) continue;
                                        int tx = col + dx[turnDir], ty = row + dy[turnDir];
                                        if (tx >= 0 && tx < cfg.gridWidth && ty >= 0 && ty < cfg.gridHeight) {
                                            transitions.push_back(computeStateVar(route, tx, ty, reverseDir[turnDir], 
                                                                                   bends + 1, cfg.gridWidth, cfg.gridHeight, cfg.maxBends));
                                        }
                                    }
                                }
                            }
                            
                            if (!transitions.empty()) {
                                std::vector<int> implication = transitions;
                                implication.insert(implication.begin(), -currentState);
                                cm.insert(implication);
                                
                                if (transitions.size() > 1) {
                                    for (size_t i = 0; i < transitions.size(); ++i) {
                                        for (size_t j = i + 1; j < transitions.size(); ++j) {
                                            cm.insert({-currentState, -transitions[i], -transitions[j]});
                                        }
                                    }
                                }
                            } else {
                                cm.insert({-currentState});
                            }
                        }
                    }
                }
            }
            
            // Cell occupancy linking
            for (int row = 0; row < cfg.gridHeight; ++row) {
                for (int col = 0; col < cfg.gridWidth; ++col) {
                    int cellOccupancy = computeCellVar(route, col, row, cfg.gridWidth, cfg.gridHeight);
                    std::vector<int> statesHere;
                    
                    for (int bends = 0; bends <= cfg.maxBends; ++bends) {
                        for (int dir = 0; dir < 5; ++dir) {
                            int stateVar = computeStateVar(route, col, row, dir, bends, 
                                                            cfg.gridWidth, cfg.gridHeight, cfg.maxBends);
                            cm.insert({-stateVar, cellOccupancy});
                            statesHere.push_back(stateVar);
                        }
                    }
                    
                    std::vector<int> reverse = statesHere;
                    reverse.insert(reverse.begin(), -cellOccupancy);
                    cm.insert(reverse);
                    
                    cm.insertPairwiseExclusion(statesHere);
                }
            }
        }
        
        // Global cell exclusivity
        for (int row = 0; row < cfg.gridHeight; ++row) {
            for (int col = 0; col < cfg.gridWidth; ++col) {
                std::vector<int> routeOccupancies;
                for (int route = 0; route < cfg.routeCount; ++route) {
                    routeOccupancies.push_back(computeCellVar(route, col, row, cfg.gridWidth, cfg.gridHeight));
                }
                if (routeOccupancies.size() > 1) {
                    cm.insertPairwiseExclusion(routeOccupancies);
                }
            }
        }
        
        // Hotspot requirements
        for (const auto& hotspot : cfg.hotspots) {
            std::vector<int> coverage;
            for (int route = 0; route < cfg.routeCount; ++route) {
                coverage.push_back(computeCellVar(route, hotspot.x, hotspot.y, cfg.gridWidth, cfg.gridHeight));
            }
            if (!coverage.empty()) {
                cm.insert(coverage);
            }
        }
    }
}

int main(int argc, char* argv[]) {
    if (argc != 2) {
        std::cerr << "Usage: ./encoder <problem_name>" << std::endl;
        return 1;
    }
    
    std::string problemName = argv[1];
    Config cfg;
    ClauseManager clauseMgr;
    
    // Read input
    std::ifstream input(problemName + ".city");
    input >> cfg.scenarioType >> cfg.gridWidth >> cfg.gridHeight >> cfg.routeCount >> cfg.maxBends;
    if (cfg.scenarioType == 2) input >> cfg.hotspotCount; else cfg.hotspotCount = 0;
    
    for (int i = 0; i < cfg.routeCount; ++i) {
        Route r;
        r.lineNum = i;
        input >> r.origin.x >> r.origin.y >> r.destination.x >> r.destination.y;
        cfg.routes.push_back(r);
    }
    
    if (cfg.scenarioType == 2 && cfg.hotspotCount > 0) {
        for (int i = 0; i < cfg.hotspotCount; ++i) {
            Coord h;
            input >> h.x >> h.y;
            cfg.hotspots.push_back(h);
        }
    }
    input.close();
    
    // Generate constraints
    int varCount = 0;
    if (cfg.scenarioType == 1) {
        ScenarioA::generateConstraints(cfg, clauseMgr);
        varCount = ScenarioA::nextVarId - 1;
    } else {
        ScenarioB::generateConstraints(cfg, clauseMgr);
        varCount = ScenarioB::baseVarId - 1;
    }
    
    // Write SAT input
    std::ofstream satOutput(problemName + ".satinput");
    satOutput << "p cnf " << varCount << " " << clauseMgr.count() << "\n";
    for (const auto& clause : clauseMgr.getClauses()) {
        for (int lit : clause) satOutput << lit << " ";
        satOutput << "0\n";
    }
    satOutput.close();
    
    // Write variable map for Scenario A
    if (cfg.scenarioType == 1) {
        std::ofstream mapOutput(problemName + ".varmap");
        mapOutput << varCount << "\n";
        for (const auto& entry : ScenarioA::symbolTable) {
            mapOutput << entry.second;
            for (int val : entry.first) mapOutput << " " << val;
            mapOutput << "\n";
        }
        mapOutput.close();
    }
    
    std::cerr << "\n=== ENCODING COMPLETE ===" << std::endl;
    std::cerr << "Scenario: " << cfg.scenarioType << std::endl;
    std::cerr << "Clauses: " << clauseMgr.count() << std::endl;
    std::cerr << "Variables: " << varCount << std::endl;
    
    return 0;
}