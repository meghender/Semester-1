import random
import copy
import time
from typing import List, Dict, Any, Optional, Tuple
from abc import ABC, abstractmethod

# ==================== GAME UTILITIES (STANDALONE) ====================


def in_bounds(x: int, y: int, rows: int, cols: int) -> bool:
    """Check if coordinates are within board boundaries."""
    return 0 <= x < cols and 0 <= y < rows

def top_score_row() -> int:
    """Get the row index for Circle's scoring area."""
    return 2

def bottom_score_row(rows: int) -> int:
    """Get the row index for Square's scoring area."""
    return rows - 3

def is_own_score_cell(x: int, y: int, player: str, rows: int, cols: int, score_cols: List[int]) -> bool:
    """Check if a cell is in the player's own scoring area."""
    if player == "circle":
        return (y == top_score_row()) and (x in score_cols)
    else:
        return (y == bottom_score_row(rows)) and (x in score_cols)

def is_opponent_score_cell(x: int, y: int, player: str, rows: int, cols: int, score_cols: List[int]) -> bool:
    """Check if a cell is in the opponent's scoring area."""
    if player == "circle":
        return (y == bottom_score_row(rows)) and (x in score_cols)
    else:
        return (y == top_score_row()) and (x in score_cols)

def get_opponent(player: str) -> str:
    """Get the opponent player identifier."""
    return "square" if player == "circle" else "circle"

def get_win_count(cols: int) -> int:
    """Get the number of stones needed to win based on board size."""
    if cols <= 12: return 4
    elif cols <= 14: return 5
    elif cols <= 16: return 6
    else: return 4 # डिफ़ॉल्ट

# ==================== CORE GAME LOGIC (COPIED FOR INDEPENDENCE) ====================
#

def get_river_flow_destinations(board, rx, ry, sx, sy, player, rows, cols, score_cols, river_push=False):
    destinations = []
    visited = set()
    queue = [(rx, ry)]
    while queue:
        x, y = queue.pop(0)
        if (x, y) in visited or not in_bounds(x, y, rows, cols): continue
        visited.add((x, y))
        cell = board[y][x]
        if river_push and x == rx and y == ry:
            cell = board[sy][sx]
        if cell is None:
            if is_opponent_score_cell(x, y, player, rows, cols, score_cols): pass
            else: destinations.append((x, y))
            continue
        if getattr(cell, "side", "stone") != "river": continue
        dirs = [(1, 0), (-1, 0)] if cell.orientation == "horizontal" else [(0, 1), (0, -1)]
        for dx, dy in dirs:
            nx, ny = x + dx, y + dy
            while in_bounds(nx, ny, rows, cols):
                if is_opponent_score_cell(nx, ny, player, rows, cols, score_cols): break
                next_cell = board[ny][nx]
                if next_cell is None:
                    destinations.append((nx, ny)); nx += dx; ny += dy; continue
                if nx == sx and ny == sy:
                    nx += dx; ny += dy; continue
                if getattr(next_cell, "side", "stone") == "river":
                    queue.append((nx, ny)); break
                break
    out = []
    seen = set()
    for d in destinations:
        if d not in seen: seen.add(d); out.append(d)
    return out

def compute_valid_moves(board, sx, sy, player, rows, cols, score_cols):
    if not in_bounds(sx, sy, rows, cols): return {'moves': set(), 'pushes': []}
    p = board[sy][sx]
    if p is None or p.owner != player: return {'moves': set(), 'pushes': []}
    moves = set(); pushes = []
    dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    for dx, dy in dirs:
        tx, ty = sx + dx, sy + dy
        if not in_bounds(tx, ty, rows, cols): continue
        if is_opponent_score_cell(tx, ty, player, rows, cols, score_cols): continue
        target = board[ty][tx]
        if target is None: moves.add((tx, ty))
        elif getattr(target, "side", "stone") == "river":
            flow = get_river_flow_destinations(board, tx, ty, sx, sy, player, rows, cols, score_cols)
            for d in flow: moves.add(d)
        else:
            if getattr(p, "side", "stone") == "stone":
                px, py = tx + dx, ty + dy
                if in_bounds(px, py, rows, cols) and board[py][px] is None and not is_opponent_score_cell(px, py, p.owner, rows, cols, score_cols):
                    pushes.append(((tx, ty), (px, py)))
            else:
                pushed_player = target.owner
                flow = get_river_flow_destinations(board, tx, ty, sx, sy, pushed_player, rows, cols, score_cols, river_push=True)
                for d in flow:
                    if not is_opponent_score_cell(d[0], d[1], pushed_player, rows, cols, score_cols):
                        pushes.append(((tx, ty), (d[0], d[1])))
    return {'moves': moves, 'pushes': pushes}

def validate_and_apply_move(board, move, player, rows, cols, score_cols):
    action = move.get("action")
    if action == "move":
        fr = move.get("from"); to = move.get("to")
        if not fr or not to: return False, "move needs from & to"
        fx, fy = int(fr[0]), int(fr[1]); tx, ty = int(to[0]), int(to[1])
        if not in_bounds(fx, fy, rows, cols) or not in_bounds(tx, ty, rows, cols): return False, "oob"
        if is_opponent_score_cell(tx, ty, player, rows, cols, score_cols): return False, "can't go into opponent score"
        piece = board[fy][fx]
        if piece is None or piece.owner != player: return False, "invalid piece"
        if board[ty][tx] is None:
            board[ty][tx] = piece; board[fy][fx] = None; return True, "moved"
        pushed = move.get("pushed_to")
        if not pushed: return False, "destination occupied; pushed_to required"
        ptx, pty = int(pushed[0]), int(pushed[1])
        dx = tx - fx; dy = ty - fy
        if (ptx, pty) != (tx + dx, ty + dy): return False, "invalid pushed_to"
        if not in_bounds(ptx, pty, rows, cols): return False, "oob"
        if is_opponent_score_cell(ptx, pty, player, rows, cols, score_cols): return False, "can't push into opponent score"
        if board[pty][ptx] is not None: return False, "pushed_to not empty"
        board[pty][ptx] = board[ty][tx]; board[ty][tx] = piece; board[fy][fx] = None
        return True, "move+push applied"
    elif action == "push":
        fr = move.get("from"); to = move.get("to"); pushed = move.get("pushed_to")
        if not fr or not to or not pushed: return False, "push needs from,to,pushed_to"
        fx, fy = int(fr[0]), int(fr[1]); tx, ty = int(to[0]), int(to[1]); px, py = int(pushed[0]), int(pushed[1])
        if not (in_bounds(fx, fy, rows, cols) and in_bounds(tx, ty, rows, cols) and in_bounds(px, py, rows, cols)): return False, "oob"
        pushed_player = board[ty][tx].owner if board[ty][tx] else None
        if (is_opponent_score_cell(tx, ty, player, rows, cols, score_cols) or (pushed_player and is_opponent_score_cell(px, py, pushed_player, rows, cols, score_cols))): return False, "push would enter opponent score cell"
        piece = board[fy][fx]
        if piece is None or piece.owner != player: return False, "invalid piece"
        if board[ty][tx] is None: return False, "to must be occupied"
        if board[py][px] is not None: return False, "pushed_to not empty"
        if getattr(piece, "side", "stone") == "river" and getattr(board[ty][tx], "side", "stone") == "river": return False, "rivers cannot push rivers"
        info = compute_valid_moves(board, fx, fy, player, rows, cols, score_cols)
        if ((tx, ty), (px, py)) not in info['pushes']: return False, "push pair invalid"
        board[py][px] = board[ty][tx]; board[ty][tx] = board[fy][fx]; board[fy][fx] = None
        mover = board[ty][tx]
        if getattr(mover, "side", "stone") == "river": mover.side = "stone"; mover.orientation = None
        return True, "push applied"
    elif action == "flip":
        fr = move.get("from")
        if not fr: return False, "flip needs from"
        fx, fy = int(fr[0]), int(fr[1])
        if not in_bounds(fx, fy, rows, cols): return False, "oob"
        piece = board[fy][fx]
        if piece is None or piece.owner != player: return False, "invalid piece"
        if getattr(piece, "side", "stone") == "stone":
            ori = move.get("orientation")
            if ori not in ("horizontal", "vertical"): return False, "stone->river needs orientation"
            piece.side = "river"; piece.orientation = ori
            flow = get_river_flow_destinations(board, fx, fy, fx, fy, player, rows, cols, score_cols)
            piece.side = "stone"; piece.orientation = None
            for (dx, dy) in flow:
                if is_opponent_score_cell(dx, dy, player, rows, cols, score_cols): return False, "flip would allow flow into opponent score"
            piece.side = "river"; piece.orientation = ori
            return True, "flipped to river"
        else:
            piece.side = "stone"; piece.orientation = None
            return True, "flipped to stone"
    elif action == "rotate":
        fr = move.get("from")
        if not fr: return False, "rotate needs from"
        fx, fy = int(fr[0]), int(fr[1])
        if not in_bounds(fx, fy, rows, cols): return False, "oob"
        piece = board[fy][fx]
        if piece is None or piece.owner != player: return False, "invalid"
        if getattr(piece, "side", "stone") != "river": return False, "rotate only on river"
        old_ori = piece.orientation
        piece.orientation = "horizontal" if piece.orientation == "vertical" else "vertical"
        flow = get_river_flow_destinations(board, fx, fy, fx, fy, player, rows, cols, score_cols)
        for (dx, dy) in flow:
            if is_opponent_score_cell(dx, dy, player, rows, cols, score_cols):
                piece.orientation = old_ori # Revert
                return False, "rotation allows flow into opponent score"
        return True, "rotated"
    return False, "unknown action"


# ==================== BASE AGENT CLASS ====================
class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    """
    def __init__(self, player: str):
        self.player = player
        self.opponent = get_opponent(player)
    
    @abstractmethod
    def choose(self, board: List[List[Any]], rows: int, cols: int, score_cols: List[int], current_player_time: float, opponent_time: float) -> Optional[Dict[str, Any]]:
        pass

# ==================== STUDENT AGENT ====================
class StudentAgent(BaseAgent):
    
    def __init__(self, player: str):
        super().__init__(player)
        
        # --- MINIMAX/AI VARIABLES ---
        self.transposition_table = {}
        MAX_ROWS = 17 # Zobrist टेबल के लिए मैक्स साइज
        MAX_COLS = 16
        self.zobrist_table = [[[random.randint(1, 2**64 - 1) for _ in range(4)] 
                               for _ in range(MAX_COLS)] 
                               for _ in range(MAX_ROWS)]
        self.last_turn_board_hash = None
        self.last_move_i_made = None
        self.push_loop_counter = 0

        # --- STATE MACHINE (OPENING BOOK) ---
        self.all_plans = {
            "circle": {
                12: {
                    "A": [ {"action": "flip", "from": [8, 9], "orientation": "horizontal"},
                          {"action": "move", "from": [8, 8], "to": [11, 9]}, 
                          {"action": "flip", "from": [11, 9], "orientation": "vertical"},
                          {"action": "move", "from": [7, 9], "to": [11, 2]},

                          {"action": "flip", "from": [11,9]},
                          {"action": "flip", "from": [4, 9], "orientation": "horizontal"},
                          {"action": "move", "from": [3, 9], "to": [0,9]},
                          {"action": "move", "from": [3, 8], "to": [3,9]},


                          {"action": "flip", "from": [11, 9], "orientation": "vertical"},
                          {"action": "flip", "from": [11, 2], "orientation": "horizontal"},
                          {"action": "flip", "from": [6, 9], "orientation": "horizontal"},
                             
                           {"action": "move", "from": [6, 8], "to": [4,2]},                 
                           {"action": "move", "from": [5, 9], "to": [5, 2]},                 
                           {"action": "move", "from": [4, 8], "to": [6,2]},                  
                           {"action": "move", "from": [3, 9], "to": [7, 2]}], 

                    "B1": [{"action": "move", "from": [11,2], "to": [11,1]}], 

                    "B2": [{"action": "move", "from": [6, 8], "to": [4,1]},                  
                           {"action": "move", "from": [5, 9], "to": [5,1]},                 
                           {"action": "move", "from": [4, 8], "to": [6,1]},                
                           {"action": "move", "from": [3, 9], "to": [7,1]}],


                    "C1": [{"action": "move", "from": [11,9], "to": [10,9]},
                           {"action": "move", "from": [11,2], "to": [10,2]}], 
                    
                    "C2": [{"action": "move", "from": [6, 8], "to": [4,2]},                 
                           {"action": "move", "from": [5, 9], "to": [5, 2]},                 
                           {"action": "move", "from": [4, 8], "to": [6,2]},                  
                           {"action": "move", "from": [3, 9], "to": [7, 2]}],
                    
                    "D": [{"action": "flip", "from": [11,9]}] 
                },

                14: { # Medium board
                    "A": [{"action": "flip", "from": [9,11], "orientation": "horizontal"},
                          {"action": "move", "from": [9,10], "to": [13,11]},
                          {"action": "flip", "from": [13,11], "orientation": "vertical"},
                          {"action": "move", "from": [8,11], "to": [13, 2]},

                          {"action": "flip", "from": [13,11]},
                          {"action": "flip", "from": [3,11], "orientation": "horizontal"},
                          {"action": "move", "from": [3, 10], "to": [0,11]},
                          {"action": "move", "from": [4, 10], "to": [3,10]},

                          {"action": "flip", "from": [13,11], "orientation": "vertical"},
                          {"action": "flip", "from": [13, 2], "orientation": "horizontal"},
                          
                          {"action": "flip", "from": [7,11], "orientation": "horizontal"},
                          {"action": "flip", "from": [5,11], "orientation": "horizontal"},
                          
                          {"action": "move", "from": [7,10], "to": [4,2]},
                          {"action": "move", "from": [6,11], "to": [5, 2]},
                          {"action": "move", "from": [5,10], "to": [6,2]},
                          {"action": "move", "from": [4, 11], "to": [7, 2]},
                          {"action": "move", "from": [3, 10], "to": [8, 2]}], 

                    "B1": [{"action": "move", "from": [13,2], "to": [13,1]}],

                    "B2": [{"action": "move", "from": [7,10], "to": [4,1]},
                           {"action": "move", "from": [6,11], "to": [5, 1]},
                           {"action": "move", "from": [5,10], "to": [6,1]},
                           {"action": "move", "from": [4, 11], "to":[7,1]},
                           {"action": "move", "from": [3, 10], "to":[8,1]}],

                    "C1": [{"action": "move", "from": [13,11], "to": [12,11]},
                           {"action": "move", "from": [13,2], "to": [12,2]}], 

                    "C2": [{"action": "move", "from":[7,10], "to": [4,2]},
                          {"action": "move", "from": [6,11], "to": [5, 2]},
                          {"action": "move", "from": [5,10], "to": [6,2]},
                          {"action": "move", "from": [4, 11], "to": [7, 2]},
                          {"action": "move", "from": [3, 10], "to": [8, 2]}],
                    
                    "D": [{"action": "flip", "from": [13,11]}] 
                },
                16: { # Large board
                    "A": [{"action": "flip", "from": [11,13], "orientation": "horizontal"},
                          {"action": "move", "from": [11,12], "to": [15,13]},
                          {"action": "flip", "from": [15,13], "orientation": "vertical"},
                          {"action": "move", "from": [10,13], "to": [15, 2]},

                          {"action": "flip", "from": [15,13]},
                          {"action": "flip", "from": [5,13], "orientation": "horizontal"},
                          {"action": "move", "from": [4, 13], "to": [0,13]},
                          {"action": "move", "from": [4, 12], "to": [4,13]},


                          {"action": "flip", "from": [9,13], "orientation": "horizontal"},
                          {"action": "flip", "from": [7,13], "orientation": "horizontal"},
                          {"action": "flip", "from": [15,13], "orientation": "vertical"},
                          {"action": "flip", "from": [15, 2], "orientation": "horizontal"},


                          {"action": "move", "from": [9,12], "to": [5,2]},
                          {"action": "move", "from": [8,13], "to": [6, 2]},
                          {"action": "move", "from": [7,12], "to": [7,2]},
                          {"action": "move", "from": [6,13], "to": [8, 2]},
                          {"action": "move", "from": [5, 12], "to": [9, 2]},
                          {"action": "move", "from": [4, 13], "to": [10, 2]}], 


                    "B1": [{"action": "move", "from": [15,2], "to": [15,1]}],

                    "B2": [{"action": "move", "from": [9,12], "to": [5,1]},
                          {"action": "move", "from": [8,13], "to": [6,1]},
                          {"action": "move", "from": [7,12], "to": [7,1]},
                          {"action": "move", "from": [6,13], "to": [8,1]},
                          {"action": "move", "from": [5, 12], "to": [9,1]},
                          {"action": "move", "from": [4, 13], "to": [10,1]}],

                    "C1": [{"action": "move", "from": [15,13], "to": [14,13]},
                           {"action": "move", "from": [15,2], "to": [14,2]} ], 

                    "C2": [{"action": "move", "from": [9,12], "to": [5,2]},
                          {"action": "move", "from": [8,13], "to": [6, 2]},
                          {"action": "move", "from": [7,12], "to": [7,2]},
                          {"action": "move", "from": [6,13], "to": [8, 2]},
                          {"action": "move", "from": [5, 12], "to": [9, 2]},
                          {"action": "move", "from": [4, 13], "to": [10, 2]} ],
                          
                    "D": [{"action": "flip", "from": [15,13]}] 
                }
            },

            "square": {
                12: { # Small board
                    "A": [{"action": "flip", "from": [8, 3], "orientation": "horizontal"},
                          {"action": "move", "from": [8, 4], "to": [11, 3]},
                          {"action": "flip", "from": [11, 3], "orientation": "vertical"},
                          {"action": "move", "from": [7, 3], "to": [11, 10]},

                          {"action": "flip", "from": [11,3]},
                          {"action": "flip", "from": [4, 3], "orientation": "horizontal"},
                          {"action": "move", "from": [3,3], "to": [0,3]},
                          {"action": "move", "from": [3,4], "to": [3,3]},

                          {"action": "flip", "from": [11, 3], "orientation": "vertical"},
                          {"action": "flip", "from": [6, 3], "orientation": "horizontal"},
                          {"action": "flip", "from": [11, 10], "orientation": "horizontal"},

                          {"action": "move", "from": [6,4], "to": [4,10]},
                          {"action": "move", "from": [5,3], "to": [5,10]},
                          {"action": "move", "from": [4,4], "to": [6,10]},
                          {"action": "move", "from": [3,3], "to": [7,10]} ],

                    "B1": [ {"action": "move", "from": [11,10], "to": [11, 11]}],

                    "B2": [{"action": "move", "from": [6,4], "to": [4,11]},
                          {"action": "move", "from": [5,3], "to": [5,11]},
                          {"action": "move", "from": [4,4], "to": [6,11]},
                          {"action": "move", "from": [3,3], "to": [7,11]}],

                    "C1": [{"action": "move", "from": [11,3], "to": [10,3]},
                           {"action": "move", "from": [11,10], "to": [10,10]} ],

                    "C2": [{"action": "move", "from": [6,4], "to": [4,10]},
                          {"action": "move", "from": [5,3], "to": [5,10]},
                          {"action": "move", "from": [4,4], "to": [6,10]},
                          {"action": "move", "from": [3,3], "to": [7,10]}],
                          
                    "D": [{"action": "flip", "from": [11,3]}] 
                },
                14: { # Medium board
                    "A": [{"action": "flip", "from": [9,3], "orientation": "horizontal"},
                          {"action": "move", "from": [9,4], "to": [13,3]},
                          {"action": "flip", "from": [13,3], "orientation": "vertical"},
                          {"action": "move", "from": [8,3], "to": [13, 12]},

                          {"action": "flip", "from": [13,3]},
                          {"action": "flip", "from": [3,3], "orientation": "horizontal"},
                          {"action": "move", "from": [3,4], "to": [0,3]},
                          {"action": "move", "from": [4,4], "to": [3,4]},

                          {"action": "flip", "from": [5,3], "orientation": "horizontal"},
                          {"action": "flip", "from": [7,3], "orientation": "horizontal"},
                          {"action": "flip", "from": [13,3], "orientation": "vertical"},
                          {"action": "flip", "from": [13, 12], "orientation": "horizontal"},
                          
            
                          {"action": "move", "from": [7,4], "to": [4,12]},
                          {"action": "move", "from": [6,3], "to": [5, 12]},
                          {"action": "move", "from": [5,4], "to": [6,12]},
                          {"action": "move", "from": [4, 3], "to": [7, 12]},
                          {"action": "move", "from": [3, 4], "to": [8, 12]} ],

                    "B1": [{"action": "move", "from": [13,12], "to": [13,13]}],

                    "B2": [{"action": "move", "from": [7,4], "to":[4,13]},
                          {"action": "move", "from": [6,3], "to": [5,13]},
                          {"action": "move", "from": [5,4], "to": [6,13]},
                          {"action": "move", "from": [4, 3], "to": [7,13]},
                          {"action": "move", "from": [3, 4], "to": [8,13]} ],

                    "C1": [{"action": "move", "from": [13,3], "to": [12,3]},
                           {"action": "move", "from": [13,12], "to": [12,12]}],

                    "C2": [{"action": "move", "from":[7,4], "to": [4,12]},
                          {"action": "move", "from": [6,3], "to": [5, 12]},
                          {"action": "move", "from": [5,4], "to": [6,12]},
                          {"action": "move", "from": [4, 3], "to": [7, 12]},
                          {"action": "move", "from": [3, 4], "to": [8, 12]} ],
                          
                    "D": [{"action": "flip", "from": [13,3]}] 
                },
                16: { # Large board
                    "A": [{"action": "flip", "from": [11,3], "orientation": "horizontal"},
                          {"action": "move", "from": [11,4], "to": [15,3]},
                          {"action": "flip", "from": [15,3], "orientation": "vertical"},
                          {"action": "move", "from": [10,3], "to": [15, 14]},


                          {"action": "flip", "from": [15,3]},
                          {"action": "flip", "from": [5,3], "orientation": "horizontal"},
                          {"action": "move", "from": [4,3], "to": [0,3]},
                          {"action": "move", "from": [4,4], "to": [4,3]},


                          {"action": "flip", "from": [9,3], "orientation": "horizontal"},
                          {"action": "flip", "from": [7,3], "orientation": "horizontal"},
                          {"action": "flip", "from": [15,3], "orientation": "vertical"},
                          {"action": "flip", "from": [15,14], "orientation": "horizontal"},

                          
                          {"action": "move", "from": [9,4], "to": [5,14]},
                          {"action": "move", "from": [8,3], "to": [6, 14]},
                          {"action": "move", "from": [7,4], "to": [7,14]},
                          {"action": "move", "from": [6, 3], "to": [8,14]},
                          {"action": "move", "from": [5, 4], "to": [9, 14]},
                          {"action": "move", "from": [4,3], "to": [10, 14]}],

                    "B1": [ {"action": "move", "from": [15,14], "to": [15,15]}],

                    "B2": [{"action": "move", "from": [9,4], "to": [5,15]},
                          {"action": "move", "from": [8,3], "to": [6, 15]},
                          {"action": "move", "from": [7,4], "to": [7,15]},
                          {"action": "move", "from": [6, 3], "to": [8,15]},
                          {"action": "move", "from": [5, 4], "to": [9, 15]},
                          {"action": "move", "from": [4,3], "to": [10, 15]}],

                    "C1": [{"action": "move", "from": [15,3], "to": [14,3]},
                           {"action": "move", "from": [15,14], "to": [14,14]}],

                    "C2": [{"action": "move", "from": [9,4], "to": [5,14]},
                          {"action": "move", "from": [8,3], "to": [6, 14]},
                          {"action": "move", "from": [7,4], "to": [7,14]},
                          {"action": "move", "from": [6, 3], "to": [8,14]},
                          {"action": "move", "from": [5, 4], "to": [9, 14]},
                          {"action": "move", "from": [4,3], "to": [10, 14]}],
                          
                    "D": [{"action": "flip", "from": [15,3]}] 
                }
            }
        }
       
        self.current_plan = "INIT" 
        self.active_plan_A = []
        self.active_plan_B1 = []
        self.active_plan_B2 = []
        self.active_plan_C1 = []
        self.active_plan_C2 = []
        self.active_plan_D = [] 
        
        self.plan_A_step = 0
        self.plan_B_step = 0
        self.plan_C_step = 0
        self.plan_D_step = 0 
        
        self.plan_B_combined_moves = []
        self.plan_C_combined_moves = []
        
        # --- TRACKERS FOR STALLING DETECTION ---
        self.move_count = 0
        self.corner_timers = {} 
        self.stalling_corners = set()
        self.has_breached_back_row = False
        self.back_row_timers = {}
        self.stalling_back_row = set()
        self.max_flank_progress = {}
        self.mid_row_timers = {}
        self.stalling_mid_row = set()
        self.staging_zone_timers = {}
        self.stalling_staging_zone = set()
        self.final_approach_timers = {}
        self.stalling_final_approach = set()
        self.offensive_corner_timers = {}
        self.stalling_offensive_corners = set()

        # -- ---
        self.FLANK_SIDE_COLS_MAP = {
            12: [],
            14: [],
            16: [],
        }
        self.FLANK_TRACK_COLS_MAP = {
            12: [],
            14: [],
            16: [],
        }
        self.OFFENSIVE_CORNER_COLS_MAP = {
            12: [],
            14: [],
            16: [],
        }


    def _get_board_hash(self, board, rows, cols):
        h = 0
        for r in range(rows):
            for c in range(cols):
                piece = board[r][c]
                if piece:
                    piece_type = 0
                    if piece.owner == 'circle':
                        if getattr(piece, "side", "stone") == 'river': piece_type = 1
                    else:
                        piece_type = 2
                        if getattr(piece, "side", "stone") == 'river': piece_type = 3
                    # zeborist table saving
                    if r < len(self.zobrist_table) and c < len(self.zobrist_table[0]):
                        h ^= self.zobrist_table[r][c][piece_type]
        return h
    
    def _get_game_state_score(self, board, rows, cols, score_cols):
        player_win_count, opponent_win_count = 0, 0
        player_score_row = top_score_row() if self.player == "circle" else bottom_score_row(rows)
        opponent_score_row = bottom_score_row(rows) if self.player == "circle" else top_score_row()
        
        win_count = get_win_count(cols) # DYNAMIC WIN COUNT BASED ON BOARD SIZE

        for x in score_cols:
            p_piece = board[player_score_row][x]
            if p_piece and p_piece.owner == self.player and getattr(p_piece, "side", "stone") == "stone":
                player_win_count += 1
            o_piece = board[opponent_score_row][x]
            if o_piece and o_piece.owner == self.opponent and getattr(o_piece, "side", "stone") == "stone":
                opponent_win_count += 1
        
        if player_win_count >= win_count: return float('inf')
        if opponent_win_count >= win_count: return float('-inf')
        
        return None
    
    # ==================== TRACKERS ====================
    
    def _update_all_timers(self, board, rows, cols, score_cols):
        """ STALLING TIMER UPDATION FUNCTION """
        
        # 
        track_cols = self.FLANK_TRACK_COLS_MAP.get(cols, [0, 1, cols - 2, cols - 1]) # फॉलबैक
        offensive_cols = self.OFFENSIVE_CORNER_COLS_MAP.get(cols, [0, 1, 2, cols - 3, cols - 2, cols - 1]) # फॉलबैक

        if not self.has_breached_back_row:
            own_goal_row = top_score_row() if self.player == 'circle' else bottom_score_row(rows)
            breach_rows = [r for r in range(rows) if (self.player == 'circle' and r < own_goal_row) or (self.player == 'square' and r > own_goal_row)]
            for r_check in breach_rows:
                if any(in_bounds(c_check, r_check, rows, cols) and board[r_check][c_check] and board[r_check][c_check].owner == self.player for c_check in score_cols):
                    self.has_breached_back_row = True
                    break
        
        extreme_back_row_y = 0 if self.player == 'circle' else rows - 1
        self._update_stall_timers(board, {(c, extreme_back_row_y) for c in range(cols)}, self.back_row_timers, self.stalling_back_row, 2, rows, cols)
        
        mid_rows = range(rows // 2 - 1, rows // 2) if self.player == 'circle' else range(rows // 2, rows // 2 + 1)
        self._update_stall_timers(board, {(c, r) for r in mid_rows for c in range(cols)}, self.mid_row_timers, self.stalling_mid_row, 2, rows, cols)
        
        if self.player == 'circle': staging_zone = {(c, r) for r in [0, 1] for c in [1, cols - 2]}
        else: staging_zone = {(c, r) for r in [rows-1, rows-2] for c in [1, cols-2]}
        self._update_stall_timers(board, staging_zone, self.staging_zone_timers, self.stalling_staging_zone, 2, rows, cols)
        
        if self.player == 'circle': final_approach_zone = {(c, r) for r in [0, 1, 2] for c in score_cols}
        else: final_approach_zone = {(c, r) for r in [rows-1, rows-2, rows-3] for c in score_cols}
        self._update_stall_timers(board, final_approach_zone, self.final_approach_timers, self.stalling_final_approach, 2, rows, cols)

        if self.player == 'circle': defensive_corners = {(0, rows-1), (cols-1, rows-1)}
        else: defensive_corners = {(0, 0), (cols-1, 0)}
        self._update_stall_timers(board, defensive_corners, self.corner_timers, self.stalling_corners, 6, rows, cols)
        
        if self.player == 'circle': offensive_corner_zone = {(c, r) for r in [0, 1] for c in offensive_cols}
        else: offensive_corner_zone = {(c, r) for r in [rows - 1, rows - 2] for c in offensive_cols}
        self._update_stall_timers(board, offensive_corner_zone, self.offensive_corner_timers, self.stalling_offensive_corners, 2, rows, cols)

        for c_track in track_cols: # (नया)
            for r_track in range(rows):
                if in_bounds(c_track, r_track, rows, cols):
                    p = board[r_track][c_track]
                    if p and p.owner == self.player:
                        current_progress = (rows - 1 - r_track) if self.player == 'circle' else r_track
                        if current_progress > self.max_flank_progress.get(c_track, -1):
                            self.max_flank_progress[c_track] = current_progress

    def _update_stall_timers(self, board, zone_coords, timer_dict, stall_set, stall_duration, rows, cols):
        """HELPER FUNCTION TO UPDATE STALL TIMERS"""
        current_pieces_in_zone = {pos for pos in zone_coords if in_bounds(pos[0], pos[1], rows, cols) and board[pos[1]][pos[0]] and board[pos[1]][pos[0]].owner == self.player}
        
        moved_out = set(timer_dict.keys()) - current_pieces_in_zone
        for pos in moved_out:
            if pos in timer_dict: del timer_dict[pos]
        
        for pos in current_pieces_in_zone:
            if pos not in timer_dict:
                timer_dict[pos] = self.move_count
        
        stall_set.clear()
        for pos, start_move in timer_dict.items():
            if self.move_count - start_move > stall_duration:
                stall_set.add(pos)
    
    # ====================HELPER FUNCTION TO SCAN A/B/C PLAN ====================

    def scan_region(self, board, rows, cols, region_coords: List[Tuple[int, int]]) -> Dict[str, Any]:
        stats = {
            'my_pieces': 0,
            'opp_pieces': 0,
            'empty_count': 0,
            'details': []
        }
        for x, y in region_coords:
            if not in_bounds(x, y, rows, cols): continue
            piece = board[y][x]
            detail = {'pos': (x, y)}
            
            if piece is None:
                stats['empty_count'] += 1
                detail['type'] = 'empty'
                detail['owner'] = None
            else:
                owner_prefix = 'my' if piece.owner == self.player else 'opp'
                detail['owner'] = owner_prefix
                if piece.owner == self.player: stats['my_pieces'] += 1
                else: stats['opp_pieces'] += 1
                    
                if getattr(piece, "side", "stone") == 'stone':
                    detail['type'] = f'{owner_prefix}_stone'
                else: # river
                    ori_suffix = '_h' if piece.orientation == 'horizontal' else '_v'
                    detail['type'] = f'{owner_prefix}_river{ori_suffix}'
            stats['details'].append(detail)
        return stats
    
    def scan_row_portion(self, board, rows, cols, row_to_scan: int, cols_to_scan: List[int]) -> Dict[str, Any]:
        coords_to_scan = [(c, row_to_scan) for c in cols_to_scan]
        return self.scan_region(board, rows, cols, coords_to_scan)
    
    def scan_col_portion(self, board, rows, cols, row_to_scan: List[int], cols_to_scan:int)-> Dict[str, Any]:
        coords_to_scan = [(cols_to_scan,c) for c in row_to_scan]
        return self.scan_region(board, rows, cols, coords_to_scan)

    def _get_adjacent_pieces(self, board, x, y, player, rows, cols, piece_type="any"):
        count = 0
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0: continue
                nx, ny = x + dx, y + dy
                if in_bounds(nx, ny, rows, cols):
                    piece = board[ny][nx]
                    if piece and piece.owner == player:
                        if piece_type == "any" or getattr(piece, "side", "stone") == piece_type:
                            count += 1
        return count
    
    def is_valid(self, board, move, rows, cols, score_cols):
        """
        is valid checker for plan A/B/C/D moves
        (uses 'compute_valid_moves' and 'validate_and_apply_move' functions)
        """
        if move is None:
            return False
        
        # TESTIN OF 'from'
        fx, fy = move['from']
        if not in_bounds(fx, fy, rows, cols): return False
        piece = board[fy][fx]
        if piece is None or piece.owner != self.player: return False
        
        #RIGHT MOVE USING  'compute_valid_moves'
        board_copy = copy.deepcopy(board)
        move_dict = compute_valid_moves(board_copy, fx, fy, self.player, rows, cols, score_cols)
        
        if move['action'] == 'push':
            if (tuple(move['to']), tuple(move['pushed_to'])) in move_dict['pushes']:
                return True
        if move['action'] == 'move':
            if tuple(move['to']) in move_dict['moves']:
                return True
        
        # FOR FLIP AND ROTATE USE 'validate_and_apply_move' 
        if move['action'] == 'flip' or move['action'] == 'rotate':
            ok, _ = validate_and_apply_move(
                board_copy, move, self.player, rows, cols, score_cols
            )
            return ok
            
        return False
    
    # ==================== ====================
    
    def evaluate_board_midgame(self, board: List[List[Any]], rows: int, cols: int, score_cols: List[int]) -> float:
        """
        MIDGAME EVALUATION FUNCTION
        ('Aggressor')
        """
        my_score, opp_score = 0, 0
        
        
        side_cols = self.FLANK_SIDE_COLS_MAP.get(cols, [2, 3, cols - 4, cols - 3]) # फॉलबैक

        my_n, opp_n = 0, 0
        player_score_row = top_score_row() if self.player == "circle" else bottom_score_row(rows)
        opponent_score_row = bottom_score_row(rows) if self.player == "circle" else top_score_row()
        for x in score_cols:
            p_piece = board[player_score_row][x]
            if p_piece and p_piece.owner == self.player and getattr(p_piece, "side", "stone") == "stone":
                my_n += 1
            o_piece = board[opponent_score_row][x]
            if o_piece and o_piece.owner == self.opponent and getattr(o_piece, "side", "stone") == "stone":
                opp_n += 1
        
        
        W_GOAL_STONE = 10000.0
        my_score += my_n * W_GOAL_STONE 
        opp_score += opp_n * W_GOAL_STONE
        
        score_center = (score_cols[0] + score_cols[-1]) / 2

        early_game_threat_cols = set()
        if self.move_count <= 8:
            for r_opp in range(rows):
                for c_opp in range(cols):
                    opp_piece = board[r_opp][c_opp]
                    if opp_piece and opp_piece.owner == self.opponent:
                        is_on_my_half = (self.player == 'circle' and r_opp >= rows // 2) or \
                                        (self.player == 'square' and r_opp < rows // 2)
                        if is_on_my_half and c_opp in side_cols:
                            early_game_threat_cols.add(c_opp)

        for r in range(rows):
            for c in range(cols):
                piece = board[r][c]
                if not piece: continue

                if piece.owner == self.player:
                    # for not counting goal stones again
                    if my_n > 0 and (r == player_score_row and c in score_cols):
                        continue

                    # --- Stalling Penalties ---
                    if (c, r) in self.stalling_corners: my_score -= 0
                    if (c, r) in self.stalling_back_row: my_score -= 1000
                    if (c, r) in self.stalling_mid_row: my_score -= 2000
                    if (c, r) in self.stalling_staging_zone: my_score -= 50
                    if (c, r) in self.stalling_final_approach: my_score -= 1550
                    if (c, r) in self.stalling_offensive_corners: my_score -= 50
                    
                    # --- Early Game Defense ---
                    if self.move_count <= 8 and c in early_game_threat_cols:
                        blocking_bonus = 0
                        if getattr(piece, "side", "stone") == 'stone':
                            blocking_bonus += 3000 
                            if self._get_adjacent_pieces(board, c, r, self.player, rows, cols, 'river') > 0:
                                blocking_bonus += 2500 
                        else: # River piece
                            if getattr(piece, 'orientation', '') == 'horizontal':
                                opponent_goal_row_h = bottom_score_row(rows) if self.player == 'circle' else top_score_row()
                                is_on_critical_row = (abs(r - opponent_goal_row_h) <= 1)
                                is_a_liability = False
                                if is_on_critical_row:
                                    for dx_adj in [-1, 0, 1, 2]:
                                        for dy_adj in [-1, 0, 1]:
                                            if (dy_adj == 0 and dx_adj in [0, 1]): continue
                                            check_c, check_r = c + dx_adj, r + dy_adj
                                            if in_bounds(check_c, check_r, rows, cols):
                                                adj_piece = board[check_r][check_c]
                                                if adj_piece and adj_piece.owner == self.opponent and getattr(adj_piece, "side", "stone") == 'stone':
                                                    if any(board[opponent_goal_row_h][goal_col] is None for goal_col in score_cols):
                                                        is_a_liability = True
                                                        break
                                            if is_a_liability: break
                                        if is_a_liability: break
                                if is_a_liability:
                                    blocking_bonus -= 3500
                                else:
                                    blocking_bonus += 2500
                            elif getattr(piece, 'orientation', '') == 'vertical':
                                if self._get_adjacent_pieces(board, c, r, self.opponent, rows, cols, 'stone') > 0:
                                    blocking_bonus -= 2000
                        my_score += blocking_bonus

                    # --- Stone Logic ---
                    if getattr(piece, "side", "stone") == 'stone':
                        own_goal_row = top_score_row() if self.player == 'circle' else bottom_score_row(rows)
                        opponent_goal_row = bottom_score_row(rows) if self.player == 'circle' else top_score_row()
                        is_behind_goal = (self.player == 'circle' and r < own_goal_row) or \
                                         (self.player == 'square' and r > own_goal_row)

                        if is_behind_goal:
                            if not self.has_breached_back_row and c in score_cols:
                                my_score += 40
                            
                            is_in_setup_row = (self.player == 'circle' and r == 1) or \
                                              (self.player == 'square' and r == rows - 2)
                            is_in_extreme_back_row = (self.player == 'circle' and r == 0) or \
                                                     (self.player == 'square' and r == rows - 1)

                            if is_in_setup_row and c in score_cols:
                                if board[own_goal_row][c] is None:
                                    my_score += 3000
                                else:
                                    sorted_goal_cols = sorted(score_cols, key=lambda col: abs(c - col))
                                    for goal_col in sorted_goal_cols:
                                        if board[own_goal_row][goal_col] is None:
                                            min_dist = abs(c - goal_col)
                                            if min_dist > 0:
                                                my_score += 4000 - (min_dist * 10)
                                            break
                            elif is_in_extreme_back_row:
                                if c in score_cols and board[own_goal_row][c] is None:
                                    my_score += 3000
                        
                        progress = (rows - 1 - r) / (rows - 1) if self.player == 'circle' else r / (rows - 1)
                        goal_center = sum(score_cols) / len(score_cols)
                        column_factor = max(0, (len(score_cols)/2 - abs(c - goal_center))) / (len(score_cols)/2)
                        my_score += progress * 80 + column_factor * 120

                        for dx in [-1, 0, 1]:
                            for dy in [-1, 0, 1]:
                                if dx == 0 and dy == 0: continue
                                nx, ny = c + dx, r + dy
                                if in_bounds(nx, ny, rows, cols):
                                    adj_piece = board[ny][nx]
                                    if adj_piece and getattr(adj_piece, "side", "stone") == 'river':
                                        if adj_piece.owner == self.player:
                                            my_score += 250 
                                        else: 
                                            if getattr(adj_piece, 'orientation', '') == 'vertical':
                                                my_score += 200 
                                            else:
                                                my_score -= 300 
                        
                        is_on_opponent_half = (self.player == 'circle' and r < rows // 2) or \
                                              (self.player == 'square' and r > rows // 2)
                        
                        if is_on_opponent_half:
                            my_score += (progress * (rows - 1)) * 85
                            my_score += (cols // 2 - abs(c - score_center)) * 25
                            
                            if c in side_cols:
                                my_score += 200 + (progress * 100)
                                current_progress_val = (rows - 1 - r) if self.player == 'circle' else r
                                if current_progress_val < self.max_flank_progress.get(c, -1):
                                    my_score -= 500
                                
                                center_attack_bonus = 0
                                if self.player == 'circle' and r in [0, 1, 2]:
                                    if c in [0, 1] and in_bounds(c + 1, r, rows, cols) and board[r][c + 1] is None: center_attack_bonus = 800
                                    elif c in [cols - 2, cols - 1] and in_bounds(c - 1, r, rows, cols) and board[r][c - 1] is None: center_attack_bonus = 800
                                elif self.player == 'square' and r in [rows - 1, rows - 2, rows - 3]:
                                    if c in [0, 1] and in_bounds(c + 1, r, rows, cols) and board[r][c + 1] is None: center_attack_bonus = 800
                                    elif c in [cols - 2, cols - 1] and in_bounds(c - 1, r, rows, cols) and board[r][c - 1] is None: center_attack_bonus = 800
                                my_score += center_attack_bonus
                            
                            direction = -1 if self.player == 'circle' else 1
                            path_blocked = any(in_bounds(c, r + i * direction, rows, cols) and board[r + i * direction][c] is not None for i in range(1, abs(r - opponent_goal_row) + 1))
                            
                            if path_blocked:
                                best_flank_bonus = 0
                                for dx_flank in [-1, 1]:
                                    for i_flank in range(1, cols // 2):
                                        check_c_flank = c + i_flank * dx_flank
                                        if check_c_flank in side_cols and all(in_bounds(c + j * dx_flank, r, rows, cols) and board[r][c + j * dx_flank] is None for j in range(1, i_flank + 1)):
                                            if all(in_bounds(check_c_flank, r + k * direction, rows, cols) and board[r + k * direction][check_c_flank] is None for k in range(1, abs(r - opponent_goal_row) + 1)):
                                                flank_bonus = 300 - (i_flank * 75)
                                                if flank_bonus > best_flank_bonus:
                                                    best_flank_bonus = flank_bonus
                                                break 
                                my_score += best_flank_bonus
                            
                            staging_bonus = 0
                            if self.player == 'circle':
                                if c == 1 and r in [0, 1] and in_bounds(c+1, r, rows, cols) and board[r][c + 1] is None: staging_bonus = 700
                                elif c == cols - 2 and r in [0, 1] and in_bounds(c-1, r, rows, cols) and board[r][c - 1] is None: staging_bonus = 700
                            else:
                                if c == 1 and r in [rows-1, rows-2] and in_bounds(c+1, r, rows, cols) and board[r][c+1] is None: staging_bonus = 700
                                elif c == cols-2 and r in [rows-1, rows-2] and in_bounds(c-1, r, rows, cols) and board[r][c-1] is None: staging_bonus = 700
                            my_score += staging_bonus

                    else: # --- River Logic ---
                        is_on_opponent_half = (self.player == 'circle' and r < rows // 2) or \
                                              (self.player == 'square' and r > rows // 2)
                        if is_on_opponent_half:
                            my_score += 200 - (abs(c - score_center) * 10)

                        if hasattr(piece, 'orientation') and piece.orientation == 'vertical':
                            if any(in_bounds(c+dx, r, rows, cols) and board[r][c+dx] and board[r][c+dx].owner == self.player and getattr(board[r][c+dx], "side", "stone") == 'stone' for dx in [-1, 1]):
                                path_bonus = 150
                                direction = 1 if self.player == 'square' else -1
                                for i in range(1, rows):
                                    scan_y = r + i * direction
                                    if not in_bounds(c, scan_y, rows, cols): break
                                    path_cell = board[scan_y][c]
                                    if path_cell is None: path_bonus += 25
                                    elif path_cell.owner == self.player and getattr(path_cell, "side", "stone") == 'river' and getattr(path_cell, 'orientation', '') == 'vertical': path_bonus += 50
                                    else: break
                                my_score += path_bonus
                            
                            opp_goal_row_v = bottom_score_row(rows) if self.player == 'circle' else top_score_row()
                            if abs(r - opp_goal_row_v) <= 2 and c in score_cols:
                                for dx_opp in [-1, 1]:
                                    if in_bounds(c+dx_opp, r, rows, cols) and board[r][c+dx_opp] and board[r][c+dx_opp].owner == self.opponent and getattr(board[r][c+dx_opp], "side", "stone") == 'stone':
                                        direction_opp = 1 if self.opponent == 'square' else -1
                                        if all(in_bounds(c, r + i * direction_opp, rows, cols) and board[r + i * direction_opp][c] is None for i in range(1, abs(r-opp_goal_row_v)+1)):
                                            my_score -= 900
                                            break
                        
                        elif hasattr(piece, 'orientation') and piece.orientation == 'horizontal':
                            if (self.player == 'circle' and r >= rows // 2) or (self.player == 'square' and r < rows // 2):
                                is_liability = False
                                opp_goal_row_h = top_score_row() if self.opponent == 'circle' else bottom_score_row(rows)
                                for dx_adj in [-1, 0, 1, 2]:
                                    for dy_adj in [-1, 0, 1]:
                                        if dy_adj == 0 and dx_adj in [0, 1]: continue
                                        check_c, check_r = c + dx_adj, r + dy_adj
                                        if in_bounds(check_c, check_r, rows, cols) and board[check_r][check_c] and board[check_r][check_c].owner == self.opponent and getattr(board[check_r][check_c], "side", "stone") == 'stone' and check_c in score_cols and board[opp_goal_row_h][check_c] is None:
                                            is_liability = True
                                            break
                                    if is_liability: break
                                
                                if is_liability: my_score -= 350
                                else:
                                    defensive_bonus = 0
                                    direction = -1 if self.player == 'circle' else 1
                                    for dx in [0, 1]:
                                        if in_bounds(c+dx, r+direction, rows, cols) and board[r+direction][c+dx] and board[r+direction][c+dx].owner == self.opponent and getattr(board[r+direction][c+dx], "side", "stone") == 'stone':
                                            defensive_bonus += 75 
                                    my_score += defensive_bonus
                
                # ---(Opponent Logic) ---
                else: 
                    # DO NOT RE-COUNT PIECES ALREADY IN GOAL
                    if opp_n > 0 and (r == opponent_score_row and c in score_cols):
                        continue

                    if (self.opponent == 'circle' and r >= rows - 3) or (self.opponent == 'square' and r <= 2):
                        my_score += 150 # 'my_score'SHOULD INCREASE  TO ENCOURAGE BLOCKING OPPONENT NEAR GOAL
                    
                    if getattr(piece, "side", "stone") == 'stone':
                        if (self.player == 'circle' and r >= rows // 2) or (self.player == 'square' and r < rows // 2):
                            for dx in [-1, 1]:
                                if in_bounds(c+dx, r, rows, cols) and board[r][c+dx] and board[r][c+dx].owner == self.player and getattr(board[r][c+dx], 'orientation', '') == 'vertical':
                                    my_score -= 200 #'my_score' BAD IF OPPONENT STONE IS NEXT TO MY VERTICAL RIVER
                                    break
                        progress = (rows - 1 - r) / (rows - 1) if self.opponent == 'circle' else r / (rows - 1)
                        opp_score += progress * 10
                        
                        for dx in [-1, 0, 1]:
                            for dy in [-1, 0, 1]:
                                if dx == 0 and dy == 0: continue
                                nx, ny = c + dx, r + dy
                                if in_bounds(nx, ny, rows, cols):
                                    adj_piece = board[ny][nx]
                                    if adj_piece and getattr(adj_piece, "side", "stone") == 'river':
                                        if adj_piece.owner == self.opponent:
                                            opp_score += 250 
                                        else: 
                                            if getattr(adj_piece, 'orientation', '') == 'vertical':
                                                opp_score += 200 
                                            else:
                                                opp_score -= 300 

                        if ((self.opponent == 'circle' and r < rows // 2) or (self.opponent == 'square' and r > rows // 2)) and c in side_cols:
                            opp_score += 130
                    else:
                        if (self.opponent == 'circle' and r < rows // 2) or (self.opponent == 'square' and r > rows // 2):
                            opp_score += 20
                            
        return my_score - opp_score

    # ==================== MOVE GENERATION & ORDERING ====================

    def _generate_safe_moves(self, board, player, rows, cols, score_cols):
        """
         by using 'compute_valid_moves' to generate moves while avoiding unnecessary risks.
        """
        moves = []
        player_goal_row = top_score_row() if player == "circle" else bottom_score_row(rows)
        for y in range(rows):
            for x in range(cols):
                p = board[y][x]
                if not p or p.owner != player: continue
                
                # pieces already in goal row should not move
                if getattr(p, "side", "stone") == "stone" and y == player_goal_row and x in score_cols:
                    continue 
                
                targets = compute_valid_moves(board, x, y, player, rows, cols, score_cols)
                for (tx,ty) in targets.get('moves', set()): 
                    moves.append({"action":"move", "from":[x,y], "to":[tx,ty]})
                for ((tx,ty),(px,py)) in targets.get('pushes', []): 
                    moves.append({"action":"push","from":[x,y], "to":[tx,ty], "pushed_to":[px,py]})
                
                # don't need to consider flip/rotate for river pieces
                # COMPUTE VALID MOVES ALREADY HANDLES ILLEGAL FLIPS/ROTATES
                if getattr(p, "side", "stone") == "stone":
                    moves.append({"action":"flip","from":[x,y],"orientation":"horizontal"})
                    moves.append({"action":"flip","from":[x,y],"orientation":"vertical"})
                else:
                    moves.append({"action":"flip","from":[x,y]})
                    moves.append({"action":"rotate","from":[x,y]})
        return moves

    def _order_moves(self, board, moves, rows, cols, score_cols, is_maximizing):
        """
        FOR SORTING MOVES SO THAT ALPHA-BETA PRUNING IS MORE EFFECTIVE
        """
        move_scores = []
        player = self.player if is_maximizing else self.opponent
        my_score_row = top_score_row() if player == "circle" else bottom_score_row(rows)

        for move in moves:
            score = 0
            if move['action'] == 'move':
                to_pos = move['to']
                if is_own_score_cell(to_pos[0], to_pos[1], player, rows, cols, score_cols):
                    score = 10000 # विनिंग मूव को सबसे पहले
            elif move['action'] == 'push':
                pushed_to_pos = move['pushed_to']
                pushed_piece_pos = move['to']
                pushed_piece = board[pushed_piece_pos[1]][pushed_piece_pos[0]]
                if pushed_piece and pushed_piece.owner == player:
                    if is_own_score_cell(pushed_to_pos[0], pushed_to_pos[1], player, rows, cols, score_cols):
                        score = 10000 # विनिंग मूव
            
            # preference to move pieces closer to scoring row
            if move['action'] == 'flip' and self.move_count < 6:
                score = 10
                
            move_scores.append((score, move))
            
        move_scores.sort(key=lambda x: x[0], reverse=True)
        return [move for score, move in move_scores]

    # ==================== ALPHA-BETA SEARCH ====================

    def _alpha_beta(self, board, depth, alpha, beta, is_maximizing, rows, cols, score_cols):
        board_hash = self._get_board_hash(board, rows, cols)
        if board_hash in self.transposition_table and self.transposition_table[board_hash]['depth'] >= depth:
            return self.transposition_table[board_hash]['score'], None

        game_state_score = self._get_game_state_score(board, rows, cols, score_cols)
        if game_state_score is not None: return game_state_score, None

        if depth == 0:
            # --- CLALLING MIDGAME BRAIN ---
            return self.evaluate_board_midgame(board, rows, cols, score_cols), None

        player = self.player if is_maximizing else self.opponent
        moves = self._generate_safe_moves(board, player, rows, cols, score_cols)
        moves = self._order_moves(board, moves, rows, cols, score_cols, is_maximizing)
        if not moves: return 0, None
        
        best_move = None
        
        if is_maximizing:
            max_eval = float('-inf')
            for move in moves:
                board_copy = copy.deepcopy(board)
                ok, _ = validate_and_apply_move(board_copy, move, player, rows, cols, score_cols)
                if ok: # consider ONLY LEGAL MOVES
                    evaluation, _ = self._alpha_beta(board_copy, depth - 1, alpha, beta, False, rows, cols, score_cols)
                    if evaluation > max_eval:
                        max_eval = evaluation
                        best_move = move
                    alpha = max(alpha, evaluation)
                    if beta <= alpha: break
            self.transposition_table[board_hash] = {'score': max_eval, 'depth': depth}
            return max_eval, best_move
        else:
            min_eval = float('inf')
            for move in moves:
                board_copy = copy.deepcopy(board)
                ok, _ = validate_and_apply_move(board_copy, move, player, rows, cols, score_cols)
                if ok: # ONLY CONSIDER LEGAL MOVES
                    evaluation, _ = self._alpha_beta(board_copy, depth - 1, alpha, beta, True, rows, cols, score_cols)
                    if evaluation < min_eval:
                        min_eval = evaluation
                        best_move = move
                    beta = min(beta, evaluation)
                    if beta <= alpha: break
            self.transposition_table[board_hash] = {'score': min_eval, 'depth': depth}
            return min_eval, best_move
            
    # ==================== PLAN B/C/D HELPERS ====================

    def build_plan_B(self, plan_A_remaining_count):
      k = plan_A_remaining_count
      if k < 0: k = 0
      if k > len(self.active_plan_B2): k = len(self.active_plan_B2)
      updated_B2 = self.active_plan_B2[-k:] if k > 0 else []
      self.plan_B_combined_moves = self.active_plan_B1 + updated_B2
      self.plan_B_step = 0

    def execute_plan_B(self, board, rows, cols, score_cols):
        if self.plan_B_step < len(self.plan_B_combined_moves):
            move_to_try = self.plan_B_combined_moves[self.plan_B_step]
            if self.is_valid(board, move_to_try, rows, cols, score_cols):
                self.plan_B_step += 1
                return move_to_try
            else:
                return None # if plan B fails
        else:
            return None # if plan B is done
    
    def build_plan_C(self, plan_A_remaining_count):
      k = plan_A_remaining_count
      if k < 0: k = 0
      if k > len(self.active_plan_C2): k = len(self.active_plan_C2)
      updated_C2 = self.active_plan_C2[-k:] if k > 0 else []
      self.plan_C_combined_moves = self.active_plan_C1 + updated_C2
      self.plan_C_step = 0
    
    def execute_plan_C(self, board, rows, cols, score_cols):
        if self.plan_C_step < len(self.plan_C_combined_moves):
            move_to_try = self.plan_C_combined_moves[self.plan_C_step]
            if self.is_valid(board, move_to_try, rows, cols, score_cols):
                self.plan_C_step += 1
                return move_to_try
            else:
                return None # Plan C fail
        else:
            return None # Plan C done
    
    # --- new ---
    def build_plan_D(self):
        """ loads Plan D moves into the executor. """
        self.plan_D_step = 0
    
    # --- new ---
    def execute_plan_D(self, board, rows, cols, score_cols):
        """tries to execute Plan D moves"""
        if self.plan_D_step < len(self.active_plan_D):
            move_to_try = self.active_plan_D[self.plan_D_step]
            if self.is_valid(board, move_to_try, rows, cols, score_cols):
                self.plan_D_step += 1
                return move_to_try
            else:
                return None # Plan D fail
        else:
            return None # Plan D completed
        
    # ==================== PLAN B/C CONDITION CHECKERS ====================

    def check_condition_1(self, board, rows, cols, remaining_moves_count):
        """CHECK 1 (Plan B Trigger)"""
        row_to_scan = 0
        cols_to_scan = []
        if self.player == 'circle':
            if cols == 12: row_to_scan = 2; cols_to_scan = [8,9,10] 
            elif cols == 14: row_to_scan = 2; cols_to_scan = [9,10,11,12]
            elif cols == 16: row_to_scan = 2; cols_to_scan = [11,12,13,14]
        else: # 'square'
            if cols == 12: row_to_scan = 10; cols_to_scan = [8,9,10]
            elif cols == 14: row_to_scan = 12; cols_to_scan = [9,10,11,12]
            elif cols == 16: row_to_scan = 14; cols_to_scan = [11,12,13,14]
        
        if not cols_to_scan: return False
        stats = self.scan_row_portion(board, rows, cols, row_to_scan, cols_to_scan)
        for detail in stats['details']:
            if detail['owner'] == 'opp':
                if detail['type'] == 'opp_stone' or detail['type'] == 'opp_river_v':
                    return True
        return False
    
    def check_condition_2(self, board, rows, cols, remaining_moves_count):
        """CHECK 2 (Plan C Trigger)"""
        cols_to_scan = 0
        row_to_scan = []
        if self.player == 'circle':
            if cols == 12: cols_to_scan = 11; row_to_scan = [3,4,5,6,7,8] 
            elif cols == 14: cols_to_scan = 13; row_to_scan = [3,4,5,6,7,8,9,10]
            elif cols == 16: cols_to_scan = 15; row_to_scan = [3,4,5,6,7,8,9,10,11,12]
        else: # 'square'
            if cols == 12: cols_to_scan = 11; row_to_scan = [4,5,6,7,8,9]
            elif cols == 14: cols_to_scan = 13; row_to_scan = [4,5,6,7,8,9,10,11]
            elif cols == 16: cols_to_scan = 15; row_to_scan = [4,5,6,7,8,9,10,11,12,13]
        
        if not cols_to_scan: return False
        stats = self.scan_col_portion(board, rows, cols, row_to_scan, cols_to_scan)
        for detail in stats['details']:
            if detail['owner'] == 'opp':
                if detail['type'] == 'opp_stone' or detail['type'] == 'opp_river_h':
                    return True
        return False

    # ==================== MINIMAX ENGINE (DYNAMIC TIME) ====================
    
    def run_minimax_search(self, board, rows, cols, score_cols, current_player_time, opponent_time):
        """
        New "MIDGAME" AI search logic hai which only looks at board size and time left to dynamically manage time.
        """
        start_time = time.time()
        best_move_so_far = None
        
        moves = self._generate_safe_moves(board, self.player, rows, cols, score_cols)
        if self.push_loop_counter >= 2 and self.last_move_i_made in moves:
            safe_moves = []
            for m in moves:
                if m != self.last_move_i_made:
                    safe_moves.append(m)
            moves = safe_moves
        
        if not moves: 
            return None
        
        best_move_so_far = random.choice(moves)

        # --- DYNAMIC TIME MANAGEMENT ---
        if cols <= 12: total_match_time_seconds = 120 
        elif cols <= 14: total_match_time_seconds = 180
        else: total_match_time_seconds = 240
        
        time_limit_for_this_move = current_player_time / 35.0

        if current_player_time < 15: time_limit_for_this_move = 0.5 
        elif time_limit_for_this_move < 1.0: time_limit_for_this_move = 1.0
        elif time_limit_for_this_move > 10.0: time_limit_for_this_move = 10.0

        #  
        MAX_SEARCH_DEPTH = 20 # 1 से बढ़ाकर 20 किया गया

        for depth in range(1, MAX_SEARCH_DEPTH + 1):
            elapsed_time = time.time() - start_time
            if (elapsed_time + 0.1) > time_limit_for_this_move: 
                break 
            
            self.transposition_table.clear()
            _, move = self._alpha_beta(board, depth, float('-inf'), float('inf'), True, rows, cols, score_cols)
            
            if move:
                best_move_so_far = move
        
        return best_move_so_far

    # ==================== MAIN CHOOSE FUNCTION (ROUTER) ====================
    
    def choose(self, board: List[List[Any]], rows: int, cols: int, score_cols: List[int], current_player_time: float, opponent_time: float) -> Optional[Dict[str, Any]]:
        """
        यह NAYA "choose" फ़ंक्शन hai. Yeh state machine ke liye "router" hai.
        (Plan D के साथ अपडेट किया गया)
        """
        
        # --- 0. TRACKERS & LOOP DETECTION ---
        self.move_count += 1
        self._update_all_timers(board, rows, cols, score_cols) 

        current_board_hash = self._get_board_hash(board, rows, cols)
        if current_board_hash == self.last_turn_board_hash and self.last_move_i_made is not None:
            self.push_loop_counter += 1
        else:
            self.push_loop_counter = 0
        self.last_turn_board_hash = current_board_hash
        
        
        # --- 1. run once INIT STATE ---
        if self.current_plan == "INIT":
            if cols not in self.all_plans[self.player]:
                self.current_plan = "MIDGAME"
            else:
                board_plans = self.all_plans[self.player][cols]
                self.active_plan_A = board_plans.get("A", [])
                self.active_plan_B1 = board_plans.get("B1", [])
                self.active_plan_B2 = board_plans.get("B2", [])
                self.active_plan_C1 = board_plans.get("C1", [])
                self.active_plan_C2 = board_plans.get("C2", [])
                self.active_plan_D = board_plans.get("D", []) # <-- नया
                
                # if plan A is empty, go to MIDGAME directly
                if not self.active_plan_A:
                    self.current_plan = "MIDGAME"
                else:
                    self.current_plan = "A" # start with plan A

        
        # --- 2. PLAN A STATE ---
        if self.current_plan == "A":
            if self.plan_A_step < len(self.active_plan_A):
                move_to_try = self.active_plan_A[self.plan_A_step]
                
                # loop detection
                if self.push_loop_counter >= 2 and move_to_try == self.last_move_i_made:
                     self.current_plan = "MIDGAME" # escape to midgame
                
                # if move from plan A is valid
                elif self.is_valid(board, move_to_try, rows, cols, score_cols):
                    self.plan_A_step += 1
                    self.last_move_i_made = move_to_try
                    return move_to_try
                
                # मif plan A generates invalid move
                else:
                    remaining_moves_count = len(self.active_plan_A) - self.plan_A_step
                    
                    if self.check_condition_1(board, rows, cols, remaining_moves_count):
                        self.current_plan = "B"
                        self.build_plan_B(remaining_moves_count) 
                    
                    elif self.check_condition_2(board, rows, cols, remaining_moves_count):
                        self.current_plan = "C"
                        self.build_plan_C(remaining_moves_count) 
                    
                    #
                    else:
                        self.current_plan = "D"
                        self.build_plan_D()
            else:
                # प्लान A पूरा हो गया
                self.current_plan = "MIDGAME"

        
        # --- 3. PLAN B STATE ---
        if self.current_plan == "B":
            move = self.execute_plan_B(board, rows, cols, score_cols)
            if move is not None:
                self.last_move_i_made = move
                return move
            else:
                # *****
                # if either plan B fails or completes, go to plan D
                self.current_plan = "D"
                self.build_plan_D()

        
        # --- 4. PLAN C STATE ---
        if self.current_plan == "C":
            move = self.execute_plan_C(board, rows, cols, score_cols)
            if move is not None:
                self.last_move_i_made = move
                return move
            else:
                # *** 
                # if plan C fails or completes, go to plan D
                self.current_plan = "D"
                self.build_plan_D()
        
        
        # --- 5. PLAN D STATE  ---
        if self.current_plan == "D":
            move = self.execute_plan_D(board, rows, cols, score_cols)
            if move is not None:
                self.last_move_i_made = move
                return move
            else:
                # ***
                # if plan D fails or completes, go to MIDGAME
                self.current_plan = "MIDGAME"

        
        # --- 6. MIDGAME STATE (Fallback) ---
        if self.current_plan == "MIDGAME":
            move = self.run_minimax_search(board, rows, cols, score_cols, current_player_time, opponent_time)
            self.last_move_i_made = move
            return move
        
        #  if due to some reason no move is selected, use minimax as fallback
        return self.run_minimax_search(board, rows, cols, score_cols, current_player_time, opponent_time)