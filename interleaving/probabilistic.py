from .ranking import Ranking
from .interleaving_method import InterleavingMethod
import numpy as np


class CumulationCache(dict):
    '''is a dict where n -> List l where...

    the item at an index i is selected in probability of
    l[i] - l[i - 1] (or just l[i] if i == 0).
    '''
    _tau_to_instance = {}

    class SumCache(dict):
        '''is a dict where n -> Sum of 1 / r^t where r is in [1, n] .'''
        _tau_to_instance = {}

        class MemberCache(dict):
            '''is a dict where r -> 1 / r^t .'''
            _tau_to_instance = {}

            def __new__(cls, tau):
                if tau not in cls._tau_to_instance:
                    cls._tau_to_instance[tau] = dict.__new__(cls, tau)
                return cls._tau_to_instance[tau]

            def __init__(self, tau):
                self.tau = tau

            def __missing__(self, r):
                self[r] = 1.0 / r ** self.tau
                return self[r]

        def __new__(cls, tau):
            if tau not in cls._tau_to_instance:
                cls._tau_to_instance[tau] = dict.__new__(cls, tau)
            return cls._tau_to_instance[tau]

        def __init__(self, tau):
            self.member_cache = self.MemberCache(tau)

        def __missing__(self, n):
            self[n] = sum([self.member_cache[r] for r in range(1, n + 1)])
            return self[n]

    def __new__(cls, tau):
        if tau not in cls._tau_to_instance:
            cls._tau_to_instance[tau] = dict.__new__(cls, tau)
        return cls._tau_to_instance[tau]

    def __init__(self, tau):
        self.sum_cache = self.SumCache(tau)
        self.member_cache = self.SumCache.MemberCache(tau)

    def __missing__(self, l):
        result = []
        numerator = 0.0
        denominator = self.sum_cache[l]
        for r in range(1, l):
            numerator += self.member_cache[r]
            result.append(numerator / denominator)
        result.append(1)
        self[l] = result
        return result

    def choice_one_of(self, l):
        n = len(l)
        f = np.random.random()
        cumulation = self[n]
        for i in range(0, n):
            if f < cumulation[i]:
                return l[i]


class Probabilistic(InterleavingMethod):
    '''Probabilistic Interleaving'''
    np.random.seed()

    def __init__(self, tau=3.0):
        self._cumulation_cache = CumulationCache(tau)

    def interleave(self, a, b):
        '''performs interleaving...

        a: a list of document IDs
        b: a list of document IDs

        Returns an instance of Ranking
        '''
        k = min(len(a), len(b))
        result = Ranking()
        result.number_of_rankers = 2
        result.rank_to_ranker_index = []
        rankings = [a[:], b[:]]  # Duplication
        for i in range(k):
            ranker_index = np.random.randint(0, 2)
            ranking = rankings[ranker_index]
            document = self._cumulation_cache.choice_one_of(ranking)
            result.append(document)
            result.rank_to_ranker_index.append(ranker_index)
            if k <= len(result):
                return result
            for r_j in rankings:
                try:
                    r_j.remove(document)
                    #  FIXME: list::remove is simple but slow
                except ValueError:
                    continue

    def multileave(self, *lists):
        '''performs multileaving...

        *lists: lists of document IDs

        Returns an instance of Ranking
        '''

        k = min(map(lambda l: len(l), lists))
        result = Ranking()
        result.rank_to_ranker_index = []
        result.number_of_rankers = len(lists)
        rankings = []
        for original_list in lists:
            rankings.append(original_list[:])  # Duplication
        while True:
            ranker_indexes = [i for i in range(0, len(rankings))]
            np.random.shuffle(ranker_indexes)
            while(0 < len(ranker_indexes)):
                ranker_index = ranker_indexes.pop()
                ranking = rankings[ranker_index]
                document = self._cumulation_cache.choice_one_of(ranking)
                result.append(document)
                result.rank_to_ranker_index.append(ranker_index)
                if k <= len(result):
                    return result
                for r_j in rankings:
                    try:
                        r_j.remove(document)
                        #  FIXME: list::remove is simple but slow
                    except ValueError:
                        continue

    def evaluate(self, ranking, clicks):
        '''evaluates rankers based on clicks

        ranking: an instance of Ranking generated by
                 Probabilistic::interleave or Probabilistic::multileave
        clicks:  a list of indices clicked by a user

        Examples of return values:
        - (1, 0, 0): The first ranking won
        - (0, 1, 0): The second ranking won
        - (0, 1, 1): The second and third rankings won
        - (0, 0, 0): Tie
        '''
        counts = [0] * ranking.number_of_rankers
        rank_to_ranker_index = ranking.rank_to_ranker_index
        for d in clicks:
            counts[rank_to_ranker_index[d]] += 1
        max_count = max(counts)
        if max_count == min(counts):  # Tie
            return tuple(0 for c in counts)
        else:
            return tuple(0 + (max_count == c) for c in counts)
            # Note that 0 + True -> 1 and that 0 + False -> 0
