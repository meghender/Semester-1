# list_adt.py
# This is a simple List class that wraps Python's built-in list
# We use this to store sequences of items like paths in the graph

class List:
    
    def __init__(self, starting_items=None):
        # This function runs when we create a new List object
        # starting_items: optional parameter - if provided, initialize list with these items
        
        if starting_items is None:
            # If no items provided, start with empty list
            self.items = []
        else:
            # If items provided, convert them to a Python list
            self.items = list(starting_items)
    
    def append(self, item):
        # This function adds an item to the end of our list
        # item: the thing we want to add
        self.items.append(item)
    
    def is_empty(self):
        # This function checks if our list has no items
        # Returns True if empty, False if it has items
        if len(self.items) == 0:
            return True
        else:
            return False
    
    def get_items(self):
        # This function returns the actual Python list inside our List object
        # We need this to access the items directly
        return self.items
    
    def __str__(self):
        # This function is called when we try to print the List
        # It converts our list to a readable string
        return str(self.items)
