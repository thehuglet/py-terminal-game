from branch_game.data_types import Node

# def tree_view_index_to_node_child_index(state: DraftingNode) -> int:
#     current_index = state.draft_node_index_in_tree_view
#     starting_index = state.starting_draft_node_index_in_tree_view
#     return current_index - starting_index


def insert_child(parent: Node, index: int, child: Node):
    """Mutates `parent`"""
    parent.children.append(child)
    child.parent = parent
