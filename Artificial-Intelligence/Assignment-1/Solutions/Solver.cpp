#include "solver.h"
#include <iostream>  
#include <cmath> 
#include <set>  
#include <vector> 
#include <string>       
#include <map> 
#include <numeric>       
#include <random>    
#include <limits>   
#include <algorithm>  
#include <chrono> 
using namespace std;


struct Distances { 
    vector<vector<double>> v_to_v_dist;
    vector<vector<double>> h_to_v_dist;
};


// calculating the delivered items
map<int, pair<int, int>> items_delivered(const Solution& sol) {
    map<int, pair<int, int>> delivered;
    for(const auto& plan : sol) {
        for(const auto& trip : plan.trips) {
            for(const auto& drop : trip.drops) {
                delivered[drop.village_id].first += drop.dry_food + drop.perishable_food;
                delivered[drop.village_id].second += drop.other_supplies;
            }
        }
    }
     return delivered;
}




// trying to make a random trip
Trip trip_creation_attempt(int heli_idx, const Solution& curr_sol, const ProblemData& prob,const Distances& d, mt19937& rng, const map<int, pair<int, int>>& needs) {
    const auto& heli = prob.helicopters[heli_idx];
    double dist_done = 0;
    // calculating distance it already flew
    for(const auto& trip : curr_sol[heli_idx].trips) {
        if(trip.drops.empty()) continue;
        double trip_dist = 0;
        int last_loc = -1;
        for(const auto& drop : trip.drops) {
            int vil_idx = drop.village_id - 1;
            if (last_loc == -1) {
                trip_dist += d.h_to_v_dist[heli_idx][vil_idx];
            } 
            else {
                trip_dist += d.v_to_v_dist[last_loc][vil_idx];
            }
            last_loc = vil_idx;
        }
        if (last_loc != -1) {
             trip_dist =trip_dist+ d.h_to_v_dist[heli_idx][last_loc];
        }
        dist_done =dist_done+ trip_dist;
    }

    if (dist_done >= prob.d_max) {
        return Trip{}; 
    }
     
    // making a route for random number of stops
    uniform_int_distribution<int> num_stops_dist(1, 4);
    int stops = num_stops_dist(rng);
    
    vector<int> route;
    vector<int> avail_v; 
    for(const auto& v : prob.villages) {
        if (needs.count(v.id) && (needs.at(v.id).first > 0 || needs.at(v.id).second > 0)) {
            avail_v.push_back(v.id - 1);
        }
    }

    if (avail_v.empty()){
        return Trip{};
    }
   
    //picking a random start village
    uniform_int_distribution<int> start_village_dist(0, avail_v.size() - 1);
    int start_idx = start_village_dist(rng);
    int curr_v_idx = avail_v[start_idx];
    route.push_back(curr_v_idx);

    // using set to check who is still left
    set<int> avail_set(avail_v.begin(), avail_v.end());
    avail_set.erase(curr_v_idx); 

    //building the remaining route
    while (route.size() < stops && !avail_set.empty()) {
        int last_v = route.back();
        int next_v = -1;
        double min_d = numeric_limits<double>::infinity(); 

        for (int neighbor_idx : avail_set) {
            double dist = d.v_to_v_dist[last_v][neighbor_idx];
            if (dist < min_d) {
                min_d = dist;
                next_v = neighbor_idx;
            }
        }
        // if we found one
        if (next_v != -1) {
            route.push_back(next_v);
            avail_set.erase(next_v);
        } else {
            break; 
        }
    }
    
    //route distance
    double r_dist = 0;
    if(route.empty()){
        return Trip{};
    }

    // total distance
    r_dist =r_dist + d.h_to_v_dist[heli_idx][route[0]];
    for(size_t i = 0; i < route.size() - 1; ++i) {
        r_dist =r_dist + d.v_to_v_dist[route[i]][route[i+1]];
    }
    r_dist =r_dist + d.h_to_v_dist[heli_idx][route.back()];

    // added(subtracted) a small epsilon for safety against floating point errors
    if (r_dist > (heli.distance_capacity - 1e-9) || (dist_done + r_dist) > (prob.d_max - 1e-9)) {
        return Trip{};
    }


    Trip trip;
    trip.dry_food_pickup = 0;
    trip.perishable_food_pickup = 0;
    trip.other_supplies_pickup = 0;
    
    double rem_w = heli.weight_capacity;
    
    const auto& dry_food = prob.packages[0];
    const auto& wet_food = prob.packages[1];
    const auto& other_pkg = prob.packages[2];

    double dry_efficiency;
    if (dry_food.weight > 0) {
        dry_efficiency = dry_food.value / dry_food.weight;
    } else {
        dry_efficiency = numeric_limits<double>::infinity();
    }

    double wet_efficiency;
    if (wet_food.weight > 0) {
        wet_efficiency = wet_food.value / wet_food.weight;
    } else {
        wet_efficiency = numeric_limits<double>::infinity();
    }

    for(int vil_idx : route) {
        int v_id = vil_idx + 1;
        
        int food_needed;
        if (needs.count(v_id)) {
            food_needed = needs.at(v_id).first;
        } else {
            food_needed = 0;
        }

        int other_needed;
        if (needs.count(v_id)) {
            other_needed = needs.at(v_id).second;
        } else {
            other_needed = 0;
        }
        
        if (food_needed <= 0 && other_needed <= 0) continue;

        Drop current_drop = {v_id, 0, 0, 0};

       
        if (other_needed > 0) {
            int can_take;
            if (other_pkg.weight > 0) {
                can_take = floor(rem_w / other_pkg.weight);
            } else {
                can_take = numeric_limits<int>::max();
            }
            int drop_amt = min(other_needed, can_take);
            if (drop_amt > 0) {
                current_drop.other_supplies = drop_amt;
                trip.other_supplies_pickup += drop_amt;
                rem_w -= drop_amt * other_pkg.weight;
            }
        }
        
        
        if (food_needed > 0) {
            if (wet_efficiency >= dry_efficiency) {
                // Prioritize perishable food
                int can_take_wet;
                if (wet_food.weight > 0) {
                    can_take_wet = floor(rem_w / wet_food.weight);
                } else {
                    can_take_wet = numeric_limits<int>::max();
                }
                int d_wet = min(food_needed, can_take_wet);
                if (d_wet > 0) {
                    current_drop.perishable_food += d_wet;
                    trip.perishable_food_pickup += d_wet;
                    rem_w -= d_wet * wet_food.weight;
                }
                
                // Fill remaining with dry food
                int can_take_dry;
                if (dry_food.weight > 0) {
                    can_take_dry = floor(rem_w / dry_food.weight);
                } else {
                    can_take_dry = numeric_limits<int>::max();
                }
                int d_dry = min(food_needed - d_wet, can_take_dry);
                if (d_dry > 0) {
                    current_drop.dry_food += d_dry;
                    trip.dry_food_pickup += d_dry;
                    rem_w -= d_dry * dry_food.weight;
                }
            } else { 
                int can_take_dry;
                if (dry_food.weight > 0) {
                    can_take_dry = floor(rem_w / dry_food.weight);
                } else {
                    can_take_dry = numeric_limits<int>::max();
                }
                int d_dry = min(food_needed, can_take_dry);
                if (d_dry > 0) {
                    current_drop.dry_food += d_dry;
                    trip.dry_food_pickup += d_dry;
                    rem_w -= d_dry * dry_food.weight;
                }
                
                int can_take_wet;
                if (wet_food.weight > 0) {
                    can_take_wet = floor(rem_w / wet_food.weight);
                } else {
                    can_take_wet = numeric_limits<int>::max();
                }
                int d_wet = min(food_needed - d_dry, can_take_wet);
                if (d_wet > 0) {
                    current_drop.perishable_food += d_wet;
                    trip.perishable_food_pickup += d_wet;
                    rem_w -= d_wet * wet_food.weight;
                }
            }
        }

        if (current_drop.dry_food > 0 || current_drop.perishable_food > 0 || current_drop.other_supplies > 0) {
            trip.drops.push_back(current_drop);
        }
    }
    
    if((trip.dry_food_pickup == 0 && trip.perishable_food_pickup == 0 && trip.other_supplies_pickup == 0) || trip.drops.empty()){
        return Trip{};
    }
    
    double t_val = 0;
    // value of the trip
    for (const auto& drop : trip.drops) {
        t_val =t_val+ drop.dry_food * dry_food.value;
        t_val =t_val+ drop.perishable_food * wet_food.value;
        t_val =t_val+ drop.other_supplies * prob.packages[2].value;
    }

    // cost of the trip
    double t_cost = heli.fixed_cost + heli.alpha * r_dist;
    if (t_val < t_cost) {
        return Trip{}; 
    }

    return trip;
}

//calculating the final score
double Compute_SolutionScore(const Solution& sol, const ProblemData& prob, const Distances& d) {
    double total_val = 0;
    double total_cost = 0;
    map<int, int> dry_food_count;
    map<int, int> perish_food_count;
    map<int, int> other_count;

    for (const auto& plan : sol) {
        for (const auto& trip : plan.trips) {
            for (const auto& drop : trip.drops) {
                dry_food_count[drop.village_id] += drop.dry_food;
                perish_food_count[drop.village_id] += drop.perishable_food;
                other_count[drop.village_id] += drop.other_supplies;
            }
        }
    }

     
    for (const auto& v : prob.villages) {
        int f_cap = v.population * 9;
        int o_cap = v.population * 1;
        total_val =total_val+ min(other_count[v.id], o_cap) * prob.packages[2].value;

        int dry_delivered = dry_food_count[v.id];
        int perish_delivered = perish_food_count[v.id];
        int total_food ;
        
        total_food= dry_delivered + perish_delivered;

        if (total_food <= f_cap) {
            total_val += dry_delivered * prob.packages[0].value;
            total_val =total_val+ perish_delivered * prob.packages[1].value;
        }
        else{
            double food_val = 0;
            if (prob.packages[1].value >= prob.packages[0].value) { 
                int p_count = min(perish_delivered, f_cap);
                food_val += p_count * prob.packages[1].value;
                 int rem_cap = f_cap - p_count;
                int d_count = min(dry_delivered, rem_cap);
                food_val += d_count * prob.packages[0].value;
            } 
            else{ 
                int d_count = min(dry_delivered, f_cap);
                food_val += d_count * prob.packages[0].value;
                int rem_cap = f_cap - d_count;
                int p_count = min(perish_delivered, rem_cap);
                food_val += p_count * prob.packages[1].value;
            }
            total_val =total_val+ food_val;
        }
    }

    int i;
    for(i = 0; i < sol.size(); ++i) {
        const auto& plan = sol[i];
        const auto& heli = prob.helicopters[i];
        double heli_dist_total = 0;
    
        for(const auto& trip : plan.trips) {
            if (trip.drops.empty()) {
                continue;
            }
            double trip_dist = 0;
            int last_loc = -1;

            for(const auto& drop : trip.drops) {
                if (drop.village_id <= 0 || (size_t)drop.village_id > prob.villages.size()){
                     return -numeric_limits<double>::infinity();
                }
                int village_idx = drop.village_id - 1; 
                if (last_loc == -1) {
                    trip_dist += d.h_to_v_dist[i][village_idx];
                } else { 
                    trip_dist += d.v_to_v_dist[last_loc][village_idx];
                }
                last_loc = village_idx;
            }

            if (last_loc != -1) {
                trip_dist += d.h_to_v_dist[i][last_loc];
            }

            // check per-trip distance limit
            if (trip_dist > heli.distance_capacity + 1e-9) {
                return -numeric_limits<double>::infinity();
            }

            heli_dist_total = heli_dist_total + trip_dist;
            total_cost = total_cost + heli.fixed_cost + heli.alpha * trip_dist;
        }

        // check total DMax for the helicopter
        if (heli_dist_total > prob.d_max + 1e-9) {
            return -numeric_limits<double>::infinity();
        }
    }

    return total_val - total_cost;
}




//SOLVER FUNCTION
Solution solve(const ProblemData& prob){
    cout << "Starting solver" << endl;
    auto t1 = chrono::steady_clock::now();
    auto t_limit = chrono::milliseconds(long(prob.time_limit_minutes * 60 * 1000 * 0.98));
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    
    Distances d;
    int num_h = prob.helicopters.size();
    int num_v = prob.villages.size();
    
    d.h_to_v_dist.resize(num_h, vector<double>(num_v));
    
    int i,j;
    for(i = 0; i < num_h; ++i) {
        
        const auto& heli = prob.helicopters[i];
        const Point& home_coords = prob.cities[heli.home_city_id - 1];
        
        for (j = 0; j < num_v; ++j) {
            // calculate distance and save it
            d.h_to_v_dist[i][j] = distance(home_coords, prob.villages[j].coords);
        }
    }

    // do it again for village to village
    d.v_to_v_dist.resize(num_v, vector<double>(num_v));
    for(i = 0; i < num_v; ++i) {
        for (j = 0; j < num_v; ++j) {
            // save distance
            d.v_to_v_dist[i][j] = distance(prob.villages[i].coords, prob.villages[j].coords);
        }
    }

    // --- Start with an empty solution ---
    Solution curr_sol(num_h);
    for(int i = 0; i < num_h; ++i) {
        curr_sol[i].helicopter_id = i + 1;
    }

    // this will be the best one
    Solution best_sol = curr_sol;

    
    double current_value = Compute_SolutionScore(curr_sol, prob, d);
    double best_value = current_value;

    double temperature = 1000.0;
    double cooling_rate = 0.99994;

    const auto& dry_food = prob.packages[0];
    const auto& wet_food = prob.packages[1];
    bool wet_food_is_better = wet_food.value > dry_food.value;


    //Main loop of simulated annealing
    while (chrono::duration_cast<chrono::milliseconds>(chrono::steady_clock::now() - t1) < t_limit) {
        Solution next_sol = curr_sol;
        
        //Generating the nbhr : - for picking  move type
        uniform_int_distribution<> move_dist(0, 9);
        int move_type = move_dist(rng);

        // for picking a helicopter
        uniform_int_distribution<> heli_dist(0, num_h - 1);
        int heli_idx = heli_dist(rng); // pick a random heli

        if (move_type < 8 || curr_sol[heli_idx].trips.empty()) { // 80% chance: ADD a trip
            map<int, pair<int, int>> delivered_goods = items_delivered(curr_sol);
            map<int, pair<int, int>> remaining_needs;
            for (const auto& v : prob.villages) {
                int food_delivered = delivered_goods.count(v.id) ? delivered_goods.at(v.id).first : 0;
                int other_delivered = delivered_goods.count(v.id) ? delivered_goods.at(v.id).second : 0;
                
                remaining_needs[v.id] = { max(0, v.population * 9 - food_delivered), max(0, v.population * 1 - other_delivered) };
            }

            Trip new_trip = trip_creation_attempt(heli_idx, curr_sol, prob, d, rng, remaining_needs);
            
            if (!new_trip.drops.empty()) { 
                next_sol[heli_idx].trips.push_back(new_trip);
            }
        } else if (move_type < 9) { // 10% chance: REMOVE a trip
            if (next_sol[heli_idx].trips.empty()) continue;
            uniform_int_distribution<> trip_dist(0, next_sol[heli_idx].trips.size() - 1);
            int trip_idx_to_remove = trip_dist(rng);
            next_sol[heli_idx].trips.erase(next_sol[heli_idx].trips.begin() + trip_idx_to_remove);
        } else { // 10% chance: SWAP packages in a trip
            if (next_sol[heli_idx].trips.empty()) continue;

            uniform_int_distribution<> trip_dist(0, next_sol[heli_idx].trips.size() - 1);
            int trip_idx = trip_dist(rng);
            
            Trip& modified_trip = next_sol[heli_idx].trips[trip_idx];
            
            int food_to_remove = wet_food_is_better ? floor(modified_trip.dry_food_pickup * 0.1) : floor(modified_trip.perishable_food_pickup * 0.1);
            if(food_to_remove == 0) continue;

            double weight_freed = wet_food_is_better ? food_to_remove * dry_food.weight : food_to_remove * wet_food.weight;
            
            double current_weight = modified_trip.dry_food_pickup * dry_food.weight 
                                  + modified_trip.perishable_food_pickup * wet_food.weight 
                                  + modified_trip.other_supplies_pickup * prob.packages[2].weight;
            
            double slack_weight = prob.helicopters[heli_idx].weight_capacity - current_weight;

            double available_weight_for_high_value = weight_freed + slack_weight;
            
            int high_value_food_to_add = 0;
            if (wet_food_is_better) {
                 if (wet_food.weight > 0) high_value_food_to_add = floor(available_weight_for_high_value / wet_food.weight);
            } else {
                if (dry_food.weight > 0) high_value_food_to_add = floor(available_weight_for_high_value / dry_food.weight);
            }
            
            if(high_value_food_to_add == 0) continue;

            // Update total pickups
            if (wet_food_is_better) {
                modified_trip.dry_food_pickup -= food_to_remove;
                modified_trip.perishable_food_pickup += high_value_food_to_add;
            } else {
                modified_trip.perishable_food_pickup -= food_to_remove;
                modified_trip.dry_food_pickup += high_value_food_to_add;
            }

            // Redistribute in drops
            int low_value_still_to_remove = food_to_remove;
            for(auto it = modified_trip.drops.rbegin(); it != modified_trip.drops.rend(); ++it){
                int& low_value_drop = wet_food_is_better ? it->dry_food : it->perishable_food;
                int can_remove = min(low_value_still_to_remove, low_value_drop);
                low_value_drop -= can_remove;
                low_value_still_to_remove -= can_remove;
                if(low_value_still_to_remove == 0) break;
            }

            int high_value_still_to_add = high_value_food_to_add;
            for(auto& drop : modified_trip.drops){
                 int& high_value_drop = wet_food_is_better ? drop.perishable_food : drop.dry_food;
                 high_value_drop += high_value_still_to_add;
                 high_value_still_to_add = 0;
                 if(high_value_still_to_add == 0) break;
            }

            // --- FIX: Clean up the state after the swap ---
            modified_trip.drops.erase(
                remove_if(modified_trip.drops.begin(), modified_trip.drops.end(),
                            [](const Drop& d) {
                                return d.dry_food == 0 && d.perishable_food == 0 && d.other_supplies == 0;
                            }),
                modified_trip.drops.end());

            if (modified_trip.drops.empty()) {
                next_sol[heli_idx].trips.erase(next_sol[heli_idx].trips.begin() + trip_idx);
            }
        }
        
        //checking the new plan to keep it or not
        double neighbor_value = Compute_SolutionScore(next_sol, prob, d);
        double score_diff = neighbor_value - current_value;

        // if better then always take it
        if (score_diff > 0) {
             curr_sol = next_sol; 
            current_value = neighbor_value;
            // if its the best ever save it
            if (current_value > best_value) {
                best_sol = curr_sol;
                best_value = current_value;
            }
        } else { 
            uniform_real_distribution<> p_dist(0.0, 1.0);
            if (p_dist(rng) < exp(score_diff / temperature)) {
                 curr_sol = next_sol;
                current_value = neighbor_value;
            }
        }
        temperature =temperature*cooling_rate;
    }

    // This final loop is a greedy check to see if any obvious, profitable trips can be added to the final solution.
    bool changed_something = true;
    while(changed_something) {
        changed_something = false;
       
        map<int, pair<int, int>> delivered_goods = items_delivered(best_sol);
        map<int, pair<int, int>> remaining_needs;
        bool still_needs_stuff = false;
        for (const auto& v : prob.villages) {
            int food_delivered_final = delivered_goods.count(v.id) ? delivered_goods.at(v.id).first : 0;
            int f_rem = max(0, (v.population * 9) - food_delivered_final);
            int other_delivered_final = delivered_goods.count(v.id) ? delivered_goods.at(v.id).second : 0;
            int o_rem = max(0, (v.population * 1) - other_delivered_final);
            
            remaining_needs[v.id] = {f_rem, o_rem};
            if (f_rem > 0 || o_rem > 0) still_needs_stuff = true; 
        }

        if (!still_needs_stuff){ 
            break;
        }

        
        for (int i = 0; i < num_h; ++i) {
            Trip last_trip = trip_creation_attempt(i, best_sol, prob, d, rng, remaining_needs);
            // if we made a trip
            if (!last_trip.drops.empty()) {
                best_sol[i].trips.push_back(last_trip);
                changed_something = true; 
                break;
            }
        }
    }

    cout << "Solver finished." << endl;
    return best_sol;
}

