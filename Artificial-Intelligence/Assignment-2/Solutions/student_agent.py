"""
Student Agent Implementation for River and Stones Game

This file contains the final, advanced implementation of the AI agent,
incorporating numerous expert-level techniques for high-performance play.
"""

import random
import copy
import time
from typing import List, Dict, Any, Optional, Tuple
from abc import ABC, abstractmethod

# ==================== GAME UTILITIES ====================
# Essential utility functions for game state analysis, copied from gameEngine for standalone use.

def in_bounds(x: int, y: int, rows: int, cols: int) -> bool:
    return 0 <= x < cols and 0 <= y < rows

def top_score_row() -> int:
    return 2

def bottom_score_row(rows: int) -> int:
    return rows - 3

def is_own_score_cell(x: int, y: int, player: str, rows: int, cols: int, score_cols: List[int]) -> bool:
    if player == "circle":
        return (y == top_score_row()) and (x in score_cols)
    else:
        return (y == bottom_score_row(rows)) and (x in score_cols)

def get_opponent(player: str) -> str:
    return "square" if player == "circle" else "circle"

# ==================== BASE AGENT CLASS ====================

class BaseAgent(ABC):
    def __init__(self, player: str):
        self.player = player
        self.opponent = get_opponent(player)
    
    @abstractmethod
    def choose(self, board: List[List[Any]], rows: int, cols: int, score_cols: List[int], current_player_time: float, opponent_time: float) -> Optional[Dict[str, Any]]:
        pass

# ==================== STUDENT AGENT IMPLEMENTATION ====================

class StudentAgent(BaseAgent):
    """
    Student Agent Implementation
    This agent uses an Iterative Deepening Alpha-Beta search algorithm with a
    heuristic evaluation function based on the official game scoring rules.
    """
    
    def __init__(self, player: str):
        super().__init__(player)
        self.transposition_table = {}
        self.zobrist_table = [[[random.randint(1, 2**64 - 1) for _ in range(4)] for _ in range(12)] for _ in range(13)]
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
        # --- NEW --- For tracking pieces stalling in the offensive corners.
        self.offensive_corner_timers = {}
        self.stalling_offensive_corners = set()


    def _get_board_hash(self, board, rows, cols):
        h = 0
        for r in range(rows):
            for c in range(cols):
                piece = board[r][c]
                if piece:
                    piece_type = 0
                    if piece.owner == 'circle':
                        if piece.side == 'river': piece_type = 1
                    else:
                        piece_type = 2
                        if piece.side == 'river': piece_type = 3
                    h ^= self.zobrist_table[r][c][piece_type]
        return h

    def _get_game_state_score(self, board, rows, cols, score_cols):
        player_win_count, opponent_win_count = 0, 0
        player_score_row = top_score_row() if self.player == "circle" else bottom_score_row(rows)
        opponent_score_row = bottom_score_row(rows) if self.player == "circle" else top_score_row()
        for x in score_cols:
            p_piece = board[player_score_row][x]
            if p_piece and p_piece.owner == self.player and p_piece.side == "stone":
                player_win_count += 1
            o_piece = board[opponent_score_row][x]
            if o_piece and o_piece.owner == self.opponent and o_piece.side == "stone":
                opponent_win_count += 1
        if player_win_count >= 4: return float('inf')
        if opponent_win_count >= 4: return float('-inf')
        return None

    def _get_adjacent_pieces(self, board, x, y, player, rows, cols, piece_type="any"):
        count = 0
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0: continue
                nx, ny = x + dx, y + dy
                if in_bounds(nx, ny, rows, cols):
                    piece = board[ny][nx]
                    if piece and piece.owner == player:
                        if piece_type == "any" or piece.side == piece_type:
                            count += 1
        return count

    def evaluate_board(self, board: List[List[Any]], rows: int, cols: int, score_cols: List[int]) -> float:
        """
        A fast and strategically sound evaluation function. It prioritizes the win
        condition while also understanding flanking maneuvers and river mobility.
        """
        my_score, opp_score = 0, 0
        
        try:
            from gameEngine import count_scoring_pieces
            my_n = count_scoring_pieces(board, self.player, rows, cols, score_cols)
            my_score += my_n * 5000 

            opp_n = count_scoring_pieces(board, self.opponent, rows, cols, score_cols)
            opp_score += opp_n * 5000
        except ImportError:
            pass
        
        side_cols = [2,3, cols - 4 ,cols - 3] 
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
                    if (c, r) in self.stalling_corners: my_score -= 0
                    if (c, r) in self.stalling_back_row: my_score -= 1000
                    if (c, r) in self.stalling_mid_row: my_score -= 2000
                    if (c, r) in self.stalling_staging_zone: my_score -= 50
                    if (c, r) in self.stalling_final_approach: my_score -= 1550
                    if (c, r) in self.stalling_offensive_corners: my_score -= 50
                    
                    # to make our bot defensive or attacker , or combination of both
                    # vary move count 0 , 500 ,some number 
                    if self.move_count <= 8 and c in early_game_threat_cols:
                        blocking_bonus = 0
                        if piece.side == 'stone':
                            blocking_bonus += 3000 
                            if self._get_adjacent_pieces(board, c, r, self.player, rows, cols, 'river') > 0:
                                blocking_bonus += 2500 
                        else: # River piece
                            if getattr(piece, 'orientation', '') == 'horizontal':
                                opponent_goal_row = bottom_score_row(rows) if self.player == 'circle' else top_score_row()
                                is_on_critical_row = (abs(r - opponent_goal_row) <= 1)
                                is_a_liability = False
                                if is_on_critical_row:
                                    for dx_adj in [-1, 0, 1, 2]:
                                        for dy_adj in [-1, 0, 1]:
                                            if (dy_adj == 0 and dx_adj in [0, 1]): continue
                                            check_c, check_r = c + dx_adj, r + dy_adj
                                            if in_bounds(check_c, check_r, rows, cols):
                                                adj_piece = board[check_r][check_c]
                                                if adj_piece and adj_piece.owner == self.opponent and adj_piece.side == 'stone':
                                                    if any(board[opponent_goal_row][goal_col] is None for goal_col in score_cols):
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

                    if piece.side == 'stone':
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
                        # Column alignment factor
                        goal_center = sum(score_cols) / len(score_cols)  # center of goal columns
                        column_factor = max(0, (len(score_cols)/2 - abs(c - goal_center))) / (len(score_cols)/2)  # 0 to 1

                        # Combine row progress and column factor
                        my_score += progress * 80 + column_factor * 120  # weights can be tune

                        for dx in [-1, 0, 1]:
                            for dy in [-1, 0, 1]:
                                if dx == 0 and dy == 0: continue
                                nx, ny = c + dx, r + dy
                                if in_bounds(nx, ny, rows, cols):
                                    adj_piece = board[ny][nx]
                                    if adj_piece and adj_piece.side == 'river':
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

                    else: # River piece
                        is_on_opponent_half = (self.player == 'circle' and r < rows // 2) or \
                                              (self.player == 'square' and r > rows // 2)
                        if is_on_opponent_half:
                            my_score += 200 - (abs(c - score_center) * 10)

                        if hasattr(piece, 'orientation') and piece.orientation == 'vertical':
                            if any(in_bounds(c+dx, r, rows, cols) and board[r][c+dx] and board[r][c+dx].owner == self.player and board[r][c+dx].side == 'stone' for dx in [-1, 1]):
                                path_bonus = 150
                                direction = 1 if self.player == 'square' else -1
                                for i in range(1, rows):
                                    scan_y = r + i * direction
                                    if not in_bounds(c, scan_y, rows, cols): break
                                    path_cell = board[scan_y][c]
                                    if path_cell is None: path_bonus += 25
                                    elif path_cell.owner == self.player and path_cell.side == 'river' and getattr(path_cell, 'orientation', '') == 'vertical': path_bonus += 50
                                    else: break
                                my_score += path_bonus
                            
                            opp_goal_row = bottom_score_row(rows) if self.player == 'circle' else top_score_row()
                            if abs(r - opp_goal_row) <= 2 and c in score_cols:
                                for dx_opp in [-1, 1]:
                                    if in_bounds(c+dx_opp, r, rows, cols) and board[r][c+dx_opp] and board[r][c+dx_opp].owner == self.opponent and board[r][c+dx_opp].side == 'stone':
                                        direction_opp = 1 if self.opponent == 'square' else -1
                                        if all(in_bounds(c, r + i * direction_opp, rows, cols) and board[r + i * direction_opp][c] is None for i in range(1, abs(r-opp_goal_row)+1)):
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
                                        if in_bounds(check_c, check_r, rows, cols) and board[check_r][check_c] and board[check_r][check_c].owner == self.opponent and board[check_r][check_c].side == 'stone' and check_c in score_cols and board[opp_goal_row_h][check_c] is None:
                                            is_liability = True
                                            break
                                    if is_liability: break
                                
                                if is_liability: my_score -= 350
                                else:
                                    defensive_bonus = 0
                                    direction = -1 if self.player == 'circle' else 1
                                    for dx in [0, 1]:
                                        if in_bounds(c+dx, r+direction, rows, cols) and board[r+direction][c+dx] and board[r+direction][c+dx].owner == self.opponent and board[r+direction][c+dx].side == 'stone':
                                            defensive_bonus += 75 
                                    my_score += defensive_bonus
                else: 
                    if (self.opponent == 'circle' and r >= rows - 3) or (self.opponent == 'square' and r <= 2):
                        my_score += 150
                    if piece.side == 'stone':
                        if (self.player == 'circle' and r >= rows // 2) or (self.player == 'square' and r < rows // 2):
                            for dx in [-1, 1]:
                                if in_bounds(c+dx, r, rows, cols) and board[r][c+dx] and board[r][c+dx].owner == self.player and getattr(board[r][c+dx], 'orientation', '') == 'vertical':
                                    my_score -= 200
                                    break
                        progress = (rows - 1 - r) / (rows - 1) if self.opponent == 'circle' else r / (rows - 1)
                        opp_score += progress * 10
                        
                        for dx in [-1, 0, 1]:
                            for dy in [-1, 0, 1]:
                                if dx == 0 and dy == 0: continue
                                nx, ny = c + dx, r + dy
                                if in_bounds(nx, ny, rows, cols):
                                    adj_piece = board[ny][nx]
                                    if adj_piece and adj_piece.side == 'river':
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
    
    def _order_moves(self, board, moves, rows, cols, score_cols, is_maximizing):
        move_scores = []
        player = self.player if is_maximizing else self.opponent
        for move in moves:
            score = 0
            if move['action'] in ['move', 'push']:
                to_pos = move.get('pushed_to', move.get('to'))
                if to_pos and is_own_score_cell(to_pos[0], to_pos[1], player, rows, cols, score_cols):
                    score = 100
            if move['action'] == 'flip' and self.move_count < 6:
                score = 10
            move_scores.append((score, move))
        move_scores.sort(key=lambda x: x[0], reverse=True)
        return [move for score, move in move_scores]

    def _generate_safe_moves(self, board, player, rows, cols, score_cols, compute_valid_moves_func):
        moves = []
        for y in range(rows):
            for x in range(cols):
                p = board[y][x]
                if not p or p.owner != player: continue
                
                targets = compute_valid_moves_func(board, x, y, player, rows, cols, score_cols)
                for (tx,ty) in targets.get('moves', set()): moves.append({"action":"move", "from":[x,y], "to":[tx,ty]})
                for ((tx,ty),(px,py)) in targets.get('pushes', []): moves.append({"action":"push","from":[x,y], "to":[tx,ty], "pushed_to":[px,py]})
                if p.side == "stone":
                    moves.append({"action":"flip","from":[x,y],"orientation":"horizontal"})
                    moves.append({"action":"flip","from":[x,y],"orientation":"vertical"})
                else:
                    moves.append({"action":"flip","from":[x,y]})
                    moves.append({"action":"rotate","from":[x,y]})
        return moves
    
    def _alpha_beta(self, board, depth, alpha, beta, is_maximizing, rows, cols, score_cols):
        board_hash = self._get_board_hash(board, rows, cols)
        if board_hash in self.transposition_table and self.transposition_table[board_hash]['depth'] >= depth:
            return self.transposition_table[board_hash]['score'], None

        game_state_score = self._get_game_state_score(board, rows, cols, score_cols)
        if game_state_score is not None: return game_state_score, None

        if depth == 0:
            return self.evaluate_board(board, rows, cols, score_cols), None

        player = self.player if is_maximizing else self.opponent
        try: 
            from gameEngine import validate_and_apply_move
            from agent import agent_compute_valid_moves as compute_valid_moves
        except ImportError: return 0, None

        moves = self._generate_safe_moves(board, player, rows, cols, score_cols, compute_valid_moves)
        moves = self._order_moves(board, moves, rows, cols, score_cols, is_maximizing)
        if not moves: return 0, None
        
        best_move = None
        
        if is_maximizing:
            max_eval = float('-inf')
            for move in moves:
                board_copy = copy.deepcopy(board)
                ok, _ = validate_and_apply_move(board_copy, move, player, rows, cols, score_cols)
                if ok:
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
                if ok:
                    evaluation, _ = self._alpha_beta(board_copy, depth - 1, alpha, beta, True, rows, cols, score_cols)
                    if evaluation < min_eval:
                        min_eval = evaluation
                        best_move = move
                    beta = min(beta, evaluation)
                    if beta <= alpha: break
            self.transposition_table[board_hash] = {'score': min_eval, 'depth': depth}
            return min_eval, best_move

    def choose(self, board: List[List[Any]], rows: int, cols: int, score_cols: List[int], current_player_time: float, opponent_time: float) -> Optional[Dict[str, Any]]:
        self.move_count += 1
        start_time = time.time()
        best_move_so_far = None

        # --- HEURISTIC TIMERS AND TRACKERS ---
        self._update_all_timers(board, rows, cols, score_cols)

        try:
            from agent import agent_compute_valid_moves as compute_valid_moves
            moves = self._generate_safe_moves(board, self.player, rows, cols, score_cols, compute_valid_moves)
            if not moves: return None
            best_move_so_far = random.choice(moves)
        except ImportError: return None

        depth_limit = 1
        time_limit = 0.18

        for depth in range(1, depth_limit + 1):
            elapsed_time = time.time() - start_time
            if elapsed_time > time_limit:
                break
            
            self.transposition_table.clear()
            _, move = self._alpha_beta(board, depth, float('-inf'), float('inf'), True, rows, cols, score_cols)
            if move:
                best_move_so_far = move
        
        return best_move_so_far

    def _update_all_timers(self, board, rows, cols, score_cols):
        if not self.has_breached_back_row:
            own_goal_row = top_score_row() if self.player == 'circle' else bottom_score_row(rows)
            breach_rows = [r for r in range(rows) if (self.player == 'circle' and r < own_goal_row) or (self.player == 'square' and r > own_goal_row)]
            for r_check in breach_rows:
                if any(board[r_check][c_check] and board[r_check][c_check].owner == self.player for c_check in score_cols):
                    self.has_breached_back_row = True
                    break
        
        extreme_back_row_y = 0 if self.player == 'circle' else rows - 1
        self._update_stall_timers(board, {(c, extreme_back_row_y) for c in range(cols)}, self.back_row_timers, self.stalling_back_row, 2)
        
        mid_rows = range(rows // 2 - 1, rows // 2) if self.player == 'circle' else range(rows // 2, rows // 2 + 1)
        self._update_stall_timers(board, {(c, r) for r in mid_rows for c in range(cols)}, self.mid_row_timers, self.stalling_mid_row, 2)
        
        if self.player == 'circle': staging_zone = {(c, r) for r in [0, 1] for c in [1, cols - 2]}
        else: staging_zone = {(c, r) for r in [rows-1, rows-2] for c in [1, cols-2]}
        self._update_stall_timers(board, staging_zone, self.staging_zone_timers, self.stalling_staging_zone, 2)
        
        if self.player == 'circle': final_approach_zone = {(c, r) for r in [0, 1, 2] for c in score_cols}
        else: final_approach_zone = {(c, r) for r in [rows-1, rows-2, rows-3] for c in score_cols}
        self._update_stall_timers(board, final_approach_zone, self.final_approach_timers, self.stalling_final_approach, 2)

        if self.player == 'circle': defensive_corners = {(0, rows-1), (cols-1, rows-1)}
        else: defensive_corners = {(0, 0), (cols-1, 0)}
        self._update_stall_timers(board, defensive_corners, self.corner_timers, self.stalling_corners, 6)
        
        if self.player == 'circle': offensive_corner_zone = {(c, r) for r in [0, 1] for c in [0, 1, 2, cols - 3, cols - 2, cols - 1]}
        else: offensive_corner_zone = {(c, r) for r in [rows - 1, rows - 2] for c in [0, 1, 2, cols - 3, cols - 2, cols - 1]}
        self._update_stall_timers(board, offensive_corner_zone, self.offensive_corner_timers, self.stalling_offensive_corners, 2)

        for c_track in [0, 1, cols - 2, cols - 1]:
            for r_track in range(rows):
                p = board[r_track][c_track]
                if p and p.owner == self.player:
                    current_progress = (rows - 1 - r_track) if self.player == 'circle' else r_track
                    if current_progress > self.max_flank_progress.get(c_track, -1):
                        self.max_flank_progress[c_track] = current_progress

    def _update_stall_timers(self, board, zone_coords, timer_dict, stall_set, stall_duration):
        current_pieces_in_zone = {pos for pos in zone_coords if in_bounds(pos[0], pos[1], len(board[0]), len(board)) and board[pos[1]][pos[0]] and board[pos[1]][pos[0]].owner == self.player}
        
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

