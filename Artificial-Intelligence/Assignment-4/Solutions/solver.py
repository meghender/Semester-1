import sys
import re
import numpy as np
from collections import defaultdict
import time

class BNEstimator:
    def __init__(self, network_file, observations_file):
        # Tunable Parameters for optimal performance
        self.alpha = 0.5  # smoothing_factor
        self.convergence_threshold = 1e-7
        self.max_iterations = 200 
        self.min_iterations = 10


        self.network = {}
        self.variable_order = []
        self.parent_map = {}
        self.child_map = defaultdict(list)
        self.evidence_data = []
        self.value_to_index = {}
        self.index_to_value = {}
        

        self.load_structure(network_file)
        self.load_evidence(observations_file)
        self.precompute_maps()

    
    def _parse_bif_var(self, bif_data: str):
        # Find all variable declarations
        var_declaration_pattern = re.compile(
            r'variable\s+(\w+)\s*\{\s*type\s+discrete\s*\[\s*\d+\s*\]\s*=\s*\{\s*([^\}]+)\s*\}\s*;',
            re.MULTILINE
        )

        for node_name, domain_string in var_declaration_pattern.findall(bif_data):
            # Parse domain values 
            domain_list = []
            for val in re.split(r'[,\s]+', domain_string):
                val = val.strip().strip('"').strip("'")
                if val:
                    domain_list.append(val)
            
            self.variable_order.append(node_name)
            self.value_to_index[node_name] = {val: idx for idx, val in enumerate(domain_list)}
            self.index_to_value[node_name] = domain_list
            self.network[node_name] = {
                "values": domain_list,
                "parents": [],
                "probabilities": {}
            }
            
    def _parse_bif_probs(self, bif_data):
                #Extract conditional probability specifications
        cpt_pattern = re.compile(
            r'probability\s*\(\s*([^\|\)]+?)\s*(?:\|\s*([^\)]+))?\s*\)\s*\{(.*?)\};',
            re.DOTALL | re.MULTILINE
        )
        
        for child_node, parents_string, cpt_body in cpt_pattern.findall(bif_data):
            child_node = child_node.strip()
            parent_list = [p.strip() for p in parents_string.split(',')] if parents_string else []
            
            self.network[child_node]["parents"] = parent_list
            self.parent_map[child_node] = parent_list
            
            # Register child relationships for each parent
            for parent_node in parent_list:
                self.child_map[parent_node].append(child_node)
            
            cpt_body = cpt_body.strip()
            if cpt_body.startswith("table"):
                #No parents-simple table
                numeric_entries = re.findall(r'[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?|-1', cpt_body)
                prob_array = [float(v) if v != '-1' else -1 for v in numeric_entries]
                self.network[child_node]["probabilities"]["()"] = np.array(prob_array)
            else:
                #Has parents-conditional table
                entry_pattern = re.compile(r'\(([^\)]+)\)\s*([^;\(]+)')
                for parent_instantiation, prob_string in entry_pattern.findall(cpt_body):
                    #Parse parent values
                    inst_values = []
                    for v in parent_instantiation.split(','):
                        v = v.strip().strip('"').strip("'")
                        if v:
                            inst_values.append(v)
                    instantiation_key = tuple(inst_values)
                    
                    #Parse probabilities
                    prob_values = re.findall(r'[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?|-1', prob_string)
                    prob_array = [float(x) if x != '-1' else -1 for x in prob_values]
                    self.network[child_node]["probabilities"][instantiation_key] = np.array(prob_array)
        
    def load_structure(self, filepath):
        
        with open(filepath, 'r') as f:
            bif_data = f.read()
        
        self._parse_bif_var(bif_data)
        self._parse_bif_probs(bif_data)

    def _parse_csv_line(self, line):
        #Handle CSV format with potential quotes
        if '","' in line or line.startswith('"'):
            #quotes
            field_values = [v.strip().strip('"') for v in line.split('","')]
            if field_values[0].startswith('"'):
                field_values[0] = field_values[0][1:]
            if field_values[-1].endswith('"'):
                field_values[-1] = field_values[-1][:-1]
        elif ',' in line:
            #without quotes
            field_values = [v.strip().strip('"').strip("'") for v in line.split(',')]
        else:
            # Space separated
            field_values = [v.strip().strip('"').strip("'") for v in line.split()]

        return field_values

    def load_evidence(self, filepath):
        #Load and encode observational data
        with open(filepath, 'r') as f:
            data_lines = f.readlines()
        
        for line in data_lines:
            line = line.strip()
            if not line: 
                continue

            field_values = self._parse_csv_line(line)
                
            # Encode values as integers
            encoded_record = []
            for node, value in zip(self.variable_order, field_values):
                if value == '?':
                    encoded_record.append(-1)
                else:
                    if value not in self.value_to_index[node]:
                        print(f"Warning: Unknown value '{value}' for variable '{node}'")
                        encoded_record.append(-1)
                    else:
                        encoded_record.append(self.value_to_index[node][value])
            self.evidence_data.append(encoded_record)
        
        self.evidence_data = np.array(self.evidence_data, dtype=np.int32)
        print(f"Loaded {len(self.evidence_data)} records with {len(self.variable_order)} variables")
    
    def precompute_maps(self):
        # Construct supporting data structures for efficient inference
        self.markov_blankets = {}
        self.parent_configurations = {}
        
        for node in self.variable_order:
            # Build Markov blanket
            neighborhood = set(self.parent_map[node])
            for child in self.child_map[node]:
                neighborhood.add(child)
                neighborhood.update(self.parent_map[child])
            neighborhood.discard(node)
            self.markov_blankets[node] = list(neighborhood)
            
            # Pre-enumerate all parent configurations
            parent_list = self.parent_map[node]
            if not parent_list:
                self.parent_configurations[node] = ["()"]
            else:
                # Generate all combinations of parent values
                def generate_configs(parents, idx=0):
                    if idx == len(parents):
                        return [[]]
                    parent = parents[idx]
                    rest_configs = generate_configs(parents, idx + 1)
                    all_configs = []
                    for val_idx in range(len(self.index_to_value[parent])):
                        for rest in rest_configs:
                            all_configs.append([val_idx] + rest)
                    return all_configs
                
                configuration_space = generate_configs(parent_list)
                self.parent_configurations[node] = [tuple(c) for c in configuration_space]
    
    def Initialize_cpts(self):
        #Initialize parameters using complete cases and intelligent imputation
        print("Initializing parameters from complete data...")
        
        frequency_tables = {}
        for node in self.variable_order:
            frequency_tables[node] = defaultdict(
                lambda: np.ones(len(self.index_to_value[node])) * self.alpha
            )
        
        # Phase 1: Leverage complete observations
        complete_observations = 0
        for record in self.evidence_data:
            if -1 not in record:
                complete_observations += 1
                for node_idx, node in enumerate(self.variable_order):
                    observed_value = record[node_idx]
                    parent_list = self.parent_map[node]
                    if not parent_list:
                        config_key = "()"
                    else:
                        config_key = tuple(record[self.variable_order.index(p)] for p in parent_list)
                    frequency_tables[node][config_key][observed_value] += 1.0
        
        print(f"Used {complete_observations} complete records for initialization")
        
        # Compute marginal distributions for imputation
        marginal_distributions = {}
        for node in self.variable_order:
            marginal_distributions[node] = np.ones(len(self.index_to_value[node])) * self.alpha
            for record in self.evidence_data:
                node_idx = self.variable_order.index(node)
                if record[node_idx] != -1:
                    marginal_distributions[node][record[node_idx]] += 1.0
            marginal_distributions[node] /= marginal_distributions[node].sum()
        
        # Phase 2: Impute and incorporate incomplete observations
        incomplete_observations = 0
        for record in self.evidence_data:
            if -1 in record:
                imputed_record = record.copy()
                # Fill missing values with mode
                for idx, value in enumerate(record):
                    if value == -1:
                        node = self.variable_order[idx]
                        imputed_record[idx]=np.argmax(marginal_distributions[node])
                
                incomplete_observations += 1
                # Weighted contribution from imputed data
                imputation_weight = 0.0
                for node_idx, node in enumerate(self.variable_order):
                    observed_value = imputed_record[node_idx]
                    parent_list = self.parent_map[node]
                    if not parent_list:
                        config_key = "()"
                    else:
                        config_key = tuple(imputed_record[self.variable_order.index(p)] for p in parent_list)
                    frequency_tables[node][config_key][observed_value] += imputation_weight
        
        print(f"Used {incomplete_observations} imputed records for better initialization")
        
        # Convert frequencies to probabilities and initialize all configurations
        for node in self.variable_order:
            num_values = len(self.index_to_value[node])
            
            # Initialize all possible parent configurations
            for config_key in self.parent_configurations[node]:
                if config_key in frequency_tables[node]:
                    freq_vector = frequency_tables[node][config_key]
                else:
                    freq_vector = np.ones(num_values) * self.alpha
                
                # Ensure correct shape
                if len(freq_vector) != num_values:
                    #print(f"Warning: Incorrect shape for {node} config {config_key}: expected {num_values}, got {len(freq_vector)}")
                    freq_vector = np.ones(num_values) * self.alpha
                
                total_count = freq_vector.sum()
                self.network[node]["probabilities"][config_key] = freq_vector / total_count
    
    def Prob_node_given_markov_blanket(self, target_node, candidate_value, observation_record):
        #Compute conditional probability P(node=value | Markov blanket)
        node_position = self.variable_order.index(target_node)
        
        # Extract parent configuration
        parent_list = self.parent_map[target_node]
        if not parent_list:
            parent_config = "()"
        else:
            parent_values = [observation_record[self.variable_order.index(p)] for p in parent_list]
            if -1 in parent_values:
                return -np.inf
            parent_config = tuple(parent_values)
        
        # Start with P(node=value | parents)
        if parent_config not in self.network[target_node]["probabilities"]:
            return -np.inf
        
        prob_val = self.network[target_node]["probabilities"][parent_config][candidate_value]
        log_conditional = np.log(prob_val + 1e-10)
        
        # Incorporate evidence from children P(child | parents)
        for child_node in self.child_map[target_node]:
            child_position = self.variable_order.index(child_node)
            child_observation = observation_record[child_position]
            
            if child_observation == -1:
                continue
            
            # Build child's parent configuration
            child_parent_list = self.parent_map[child_node]
            child_parent_config = []
            for parent in child_parent_list:
                if parent == target_node:
                    child_parent_config.append(candidate_value)
                else:
                    parent_idx = self.variable_order.index(parent)
                    parent_observation = observation_record[parent_idx]
                    if parent_observation == -1:
                        child_parent_config = None
                        break
                    child_parent_config.append(parent_observation)
            
            if child_parent_config is None:
                continue
            
            config_tuple = tuple(child_parent_config)
            if config_tuple not in self.network[child_node]["probabilities"]:
                continue
            
            child_probability = self.network[child_node]["probabilities"][config_tuple][child_observation]
            log_conditional += np.log(child_probability + 1e-10)
        
        return log_conditional
    
    def E_step_for_record(self, observation_record):
        #Compute expected sufficient statistics for single observation
        record_ess = {}
        for node in self.variable_order:
            record_ess[node] = defaultdict(lambda: np.zeros(len(self.index_to_value[node])))
        
        missing_position = -1
        missing_node = None
        
        # Identify missing variable (assumes at most one per record)
        for idx, value in enumerate(observation_record):
            if value == -1:
                missing_position = idx
                missing_node = self.variable_order[idx]
                break
        
        if missing_node is None:
            # Complete observation - add deterministic counts
            for idx, node in enumerate(self.variable_order):
                observed_value = observation_record[idx]
                parent_list = self.parent_map[node]
                if not parent_list:
                    config_key = "()"
                else:
                    config_key = tuple(observation_record[self.variable_order.index(p)] for p in parent_list)
                record_ess[node][config_key][observed_value] += 1.0
        else:
            # Incomplete observation - compute posterior distribution
            domain_size = len(self.index_to_value[missing_node])
            log_posterior = np.zeros(domain_size)
            
            # Evaluate P(missing=v | evidence) for each value
            for candidate_val in range(domain_size):
                test_record = observation_record.copy()
                test_record[missing_position] = candidate_val
                log_posterior[candidate_val] = self.Prob_node_given_markov_blanket(missing_node, candidate_val, test_record)
            
            # Normalize to get posterior distribution
            max_log = log_posterior.max()
            if max_log == -np.inf:
                # All probabilities are zero, use uniform
                posterior_probs = np.ones(domain_size) / domain_size
            else:
                log_posterior -= max_log
                posterior_probs = np.exp(log_posterior)
                posterior_probs /= posterior_probs.sum()
            
            # Accumulate fractional counts
            for idx, node in enumerate(self.variable_order):
                parent_list = self.parent_map[node]
                
                if node == missing_node:
                    # Distribute probability mass across missing variable values
                    if not parent_list:
                        config_key = "()"
                    else:
                        config_key = tuple(observation_record[self.variable_order.index(p)] for p in parent_list)
                    for candidate_val in range(domain_size):
                        record_ess[node][config_key][candidate_val] += posterior_probs[candidate_val]
                else:
                    observed_value = observation_record[idx]
                    # Check if missing variable is a parent
                    if missing_node in parent_list:
                        # Marginalize over missing parent values
                        for candidate_val in range(domain_size):
                            parent_config = []
                            for parent in parent_list:
                                if parent == missing_node:
                                    parent_config.append(candidate_val)
                                else:
                                    parent_config.append(observation_record[self.variable_order.index(parent)])
                            config_key = tuple(parent_config)
                            record_ess[node][config_key][observed_value] += posterior_probs[candidate_val]
                    else:
                        # Standard deterministic count
                        if not parent_list:
                            config_key = "()"
                        else:
                            config_key = tuple(observation_record[self.variable_order.index(p)] for p in parent_list)
                        record_ess[node][config_key][observed_value] += 1.0
        
        return record_ess
    
    def M_step(self, expected_sufficient_statistics):
        #Update parameters based on sufficient statistics
        for node in self.variable_order:
            num_values = len(self.index_to_value[node])
            for config_key in self.parent_configurations[node]:
                frequency_vector = expected_sufficient_statistics[node][config_key]
                
                # Ensure correct shape
                if len(frequency_vector) != num_values:
                    frequency_vector = np.ones(num_values) * self.alpha
                
                total_frequency = frequency_vector.sum()
                if total_frequency > 0:
                    self.network[node]["probabilities"][config_key] = frequency_vector / total_frequency
                else:
                    # Uniform distribution if no data
                    self.network[node]["probabilities"][config_key] = np.ones(num_values) / num_values
    
    def Run_EM_step(self):
        #Execute one complete EM cycle and return convergence metric
        # Cache current parameters
        cached_parameters = {}
        for node in self.variable_order:
            cached_parameters[node] = {}
            for config_key in self.parent_configurations[node]:
                cached_parameters[node][config_key] = self.network[node]["probabilities"][config_key].copy()
        
        # E-step: Aggregate sufficient statistics
        expected_sufficient_statistics = {}
        for node in self.variable_order:
            expected_sufficient_statistics[node] = defaultdict(
                lambda: np.ones(len(self.index_to_value[node])) * self.alpha
            )
        
        # Process each observation
        for observation_record in self.evidence_data:
            record_ess = self.E_step_for_record(observation_record)
            for node in self.variable_order:
                for config_key, frequencies in record_ess[node].items():
                    expected_sufficient_statistics[node][config_key] += frequencies
        
        # M-step: Update parameters
        self.M_step(expected_sufficient_statistics)
        
        # Measure parameter change
        cumulative_change = 0.0
        parameter_count = 0
        for node in self.variable_order:
            for config_key in self.parent_configurations[node]:
                old_probs = cached_parameters[node][config_key]
                new_probs = self.network[node]["probabilities"][config_key]
                
                # Ensure same shape
                if len(old_probs) != len(new_probs):
                    print(f"Warning: Shape mismatch for {node} config {config_key}: {len(old_probs)} vs {len(new_probs)}")
                    continue
                
                delta = np.abs(new_probs - old_probs).sum()
                cumulative_change += delta
                parameter_count += len(new_probs)
        
        return cumulative_change / parameter_count if parameter_count > 0 else 0.0
    
    def learn_cpts(self):
        #Execute parameter learning algorithm
        print("\n")
        print("EM Algorithm")
        print("\n")
        
        start_timestamp = time.time()
        self.Initialize_cpts()
        # 2. ADD THIS NEW RANDOM INITIALIZATION BLOCK
        #print("Initializing all CPTs with RANDOM probabilities...")
        #for node in self.variable_order:
            #num_values = len(self.index_to_value[node])
            #for config_key in self.parent_configurations[node]:
                # Create a vector of random numbers
                #random_probs = np.random.rand(num_values)
                # Normalize them to sum to 1
                #self.network[node]["probabilities"][config_key] = random_probs / #random_probs.sum()

        
        previous_delta = float('inf')
        for iteration_num in range(self.max_iterations):
            iteration_start = time.time()
            parameter_change = self.Run_EM_step()
            iteration_duration = time.time() - iteration_start
            
            print(f"Itr-> {iteration_num+1:3d}: Change = {parameter_change:.8f}  T = {iteration_duration:.2f}s")
            
            # Check convergence criteria
            if iteration_num >= self.min_iterations:
                if parameter_change < self.convergence_threshold:
                    print(f"\nConverged after {iteration_num+1} iterations")
                    break
                # Detect divergence
                if parameter_change > previous_delta * 2.0:
                    print(f"\nStopping due to increasing change")
                    break
            
            previous_delta = parameter_change
        
        total_duration = time.time() - start_timestamp
        print(f"\nTotal learning time: {total_duration:.2f}s")
        print("="*60)
    
    def Save_Network(self, output_filepath):
        #Serialize learned network to BIF format
        with open(output_filepath, 'w') as output_file:
            output_file.write('network "Unknown" {\n}\n')
            
            # Write variable declarations
            for node in self.variable_order:
                domain_values = self.index_to_value[node]
                output_file.write(f'variable {node} {{\n')
                output_file.write(f'  type discrete [ {len(domain_values)} ] = {{ {", ".join(domain_values)} }};\n')
                output_file.write('}\n')
            
            # Write probability tables
            for node in self.variable_order:
                parent_list = self.parent_map[node]
                
                if not parent_list:
                    output_file.write(f'probability ( {node} ) {{\n')
                    prob_vector = self.network[node]["probabilities"]["()"]
                    output_file.write(f'  table {", ".join(f"{p:.6f}" for p in prob_vector)};\n')
                else:
                    output_file.write(f'probability ( {node} | {", ".join(parent_list)} ) {{\n')
                    for config_key in self.parent_configurations[node]:
                        prob_vector = self.network[node]["probabilities"][config_key]
                        config_str = ", ".join(
                            self.index_to_value[parent_list[i]][config_key[i]] 
                            for i in range(len(parent_list))
                        )
                        output_file.write(f'  ({config_str}) {", ".join(f"{p:.6f}" for p in prob_vector)};\n')
                output_file.write('};\n')


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 solver.py <bif_file> <data_file>")
        sys.exit(1)
    
    bif_file = sys.argv[1]
    data_file = sys.argv[2]
    
    # Learn parameters
    estimator = BNEstimator(bif_file, data_file)
    estimator.learn_cpts()
    
    # Write output
    output_file = "solved_hailfinder.bif"
    estimator.Save_Network(output_file)
    print(f"\nSolved network written to: {output_file}")


if __name__ == "__main__":
    main()