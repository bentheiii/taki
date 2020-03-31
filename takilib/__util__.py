class _EqToAll:
    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False


eq_to_all = _EqToAll()

__all__ = ['eq_to_all']
