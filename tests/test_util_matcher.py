# Copyright 2021 Joschua Gandert
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
from dataclasses import dataclass

from quodlibet.util.matcher import ObjectListMatcher

from tests import TestCase


class TMatchBasics(TestCase):
    def test_empty_weight_not_allowed(self):
        self.assertRaises(ValueError, lambda: ObjectListMatcher({}))

    def test_negative_weights_not_allowed(self):
        self.assertRaises(ValueError, lambda: ObjectListMatcher({lambda i: int(i): -1}))


class TMatchIdentity(TestCase):
    def test_all_elements_in_both_but_different_order(self):
        matcher = ObjectListMatcher.of_identity()
        a = ["cookie", "beach", "house"]
        b = ["house", "cookie", "beach"]

        b_match_indices = matcher.get_indices(a, b)
        for a_item, b_idx in zip(a, b_match_indices, strict=False):
            assert a_item == b[b_idx]

        b = ["house", "beach", "cookie"]
        assert matcher.get_indices(a, b) == [2, 1, 0]

    def test_simple_unbalanced(self):
        matcher = ObjectListMatcher.of_identity()
        a = ["hell", "gel", "shell"]
        b = ["yell"]
        assert matcher.get_indices(a, b) == [0, None, None]

        a = ["gel", "hell", "shell"]
        assert matcher.get_indices(a, b) == [None, 0, None]

    def test_minimum_similarity(self):
        matcher = ObjectListMatcher.of_identity()
        a = ["mess", "blessed", "chess"]
        b = ["pudding", "xylophone", "yes"]
        matcher.should_store_similarity_matrix = True

        assert matcher.get_indices(a, b) == [2, 0, 1], formatted_matrix(matcher)

        matcher.minimum_similarity_ratio = 0.45
        assert matcher.get_indices(a, b) == [2, None, 1], formatted_matrix(matcher)

        matcher.minimum_similarity_ratio = 0.6
        assert matcher.get_indices(a, b) == [None, None, None], formatted_matrix(
            matcher)


class TMatchListOfSequences(TestCase):
    def test_clear_match(self):
        matcher = ObjectListMatcher.for_sequence([3, 1.5, 2])
        a = [("cacc", "cacc", 2), ("bacc", "baca", 1)]
        b = [("caba", "bacc", 2), ("abaa", "bcca", 2)]

        assert matcher.get_indices(a, b) == [0, 1]

        # test that repeating the same call doesn't change the result
        assert matcher.get_indices(a, b) == [0, 1]

        # in this case (same length), reversing arguments should result in the same list
        assert matcher.get_indices(b, a) == [0, 1]

    def test_other_now_barely_better(self):
        matcher = ObjectListMatcher.for_sequence([3, 1.5, 2])
        a = [("cacc", "cacc", 2), ("bacc", "baca", 1)]
        b = [("caba", "bacc", 1), ("abaa", "bcca", 2)]  # third element of first changed

        assert matcher.get_indices(a, b) == [1, 0]
        assert matcher.get_indices(a, b) == [1, 0]
        assert matcher.get_indices(b, a) == [1, 0]

    def test_change_weights(self):
        # same as in previous test
        matcher = ObjectListMatcher.for_sequence([3, 1.5, 2])
        a = [("cacc", "cacc", 2), ("bacc", "baca", 1)]
        b = [("caba", "bacc", 1), ("abaa", "bcca", 2)]

        matcher.update_attr_to_weight({lambda i: i[1]: 1})
        assert matcher.get_indices(a, b) == [0, 1]

    def test_double_weight(self):
        matcher = ObjectListMatcher.for_sequence([4, 2])
        a = [("Great Song", "Law", 2), ("Night Mix", "Beach", 1)]
        b = [("Great Song", "Beach", 1), ("Great Sea", "Low", 2)]

        assert matcher.get_indices(a, b) == [0, 1]

        # changed "Law" to "Low"
        a = [("Great Song", "Low", 2), ("Night Mix", "Beach", 1)]
        assert matcher.get_indices(a, b) == [1, 0]

    def test_nothing_to_match_b_to(self):
        matcher = ObjectListMatcher.for_sequence([7, 1])
        a = []
        b = [("Great Song", "Beach", 1), ("Great Sea", "Low", 2)]

        # As this returns the indices of b to match a, it always has the size of a.
        assert matcher.get_indices(a, b) == []
        assert matcher.get_indices([], []) == []

    def test_match_a_to_nothing(self):
        matcher = ObjectListMatcher.for_sequence([7, 1])
        a = [("Great Song", "Beach", 1), ("Great Sea", "Low", 2)]
        b = []

        # When no b element could be matched to an a element, -1 is used.
        assert matcher.get_indices(a, b) == [None, None]

    def test_more_in_a(self):
        matcher = ObjectListMatcher.for_sequence([7, 1])
        a = [("Great Song", "Beach", 1), ("Great Sea", "Low", 2)]
        b = [("Great Sea", "Light", 2)]

        assert matcher.get_indices(a, b) == [None, 0]

    def test_more_in_b(self):
        matcher = ObjectListMatcher.for_sequence([7, 1])
        a = [("Great Sea", "Light", 2)]
        b = [("Great Song", "Beach", 1), ("Great Sea", "Low", 2)]

        assert matcher.get_indices(a, b) == [1]

    def test_all_the_same(self):
        matcher = ObjectListMatcher.for_sequence([0.2, 0.7, 0.1])

        x = (9, 9, 9)
        assert matcher.get_indices([x, x, x], [x, x, x]) == [0, 1, 2]

    def test_numeric_if_both_good_match_current_order_preferred(self):
        # we pre-normalized the weights for clarity here (they're always normalized)
        matcher = ObjectListMatcher.for_sequence([0.6, 0.4])

        a = [(3, 2), (3, 4)]
        b = [(99, 99), (3, 3)]

        # despite having the same delta to (3, 3), here (3, 2) should be preferred to
        # (3, 4), as (3, 2) is a closer match (in terms of their indices)
        assert matcher.get_indices(a, b) == [1, 0]
        assert matcher.get_indices(b, a) == [1, 0]

    def test_numeric_asymmetry(self):
        matcher = ObjectListMatcher.for_sequence([0.6, 0.4])
        matcher.should_store_similarity_matrix = True

        a = [(3, 3), (8, 5), (9, 1)]
        b = [(9, 8), (3, 2), (3, 4)]

        # as (9, 8) is the best match for (9, 1), item (8, 5) will be matched to (3, 4)
        assert matcher.get_indices(a, b) == [1, 2, 0], formatted_matrix(matcher)

        matrix = matcher.similarity_matrix

        # matrix[0] are the match scores of element (3, 3) in a to all elements in b
        assert matrix[0][1] == matrix[0][2]

        # (9, 1) is most similar to (9, 8) and second most similar to (3, 2)
        assert matrix[2][0] > matrix[2][2]
        assert matrix[2][1] > matrix[2][2]

        # What happens here may seem confusing, but this is a result of the following
        # asymmetry: the best match in b for (9, 1) is (9, 8), but the best match in a
        # for (9, 8) isn't (9, 1), it's (8, 5). This can be seen by calculating the
        # weighted delta between (9, 8) and each of them (smaller delta = more similar):
        #   delta to (9, 1):    (9-9) * 0.6 + (8-1) * 0.4 = 2.8
        #   delta to (8, 5):    (9-8) * 0.6 + (8-5) * 0.4 = 1.8
        assert matcher.get_indices(b, a) == [1, 0, 2], formatted_matrix(matcher)

    def test_should_go_through_every_attribute(self):
        matcher = ObjectListMatcher.for_sequence([0.7, 0.3])
        matcher.should_store_similarity_matrix = True

        # There are undefeatable matches for the first attribute / weight here, and so
        # by default the algorithm will not even check the second attribute.
        a = [("a", -8), ("very clear", 0), ("way", 33), ("forward", 2)]
        b = [("very clear", 33), ("forward", -1), ("a", 5), ("way", 2)]

        assert matcher.get_indices(a, b) == [2, 0, 3, 1]
        partial_matrix = matcher.similarity_matrix

        matcher.should_go_through_every_attribute = True

        # Result definitely shouldn't change
        assert matcher.get_indices(a, b) == [2, 0, 3, 1], formatted_matrix(matcher)

        # But in this case the matrix should have
        assert matcher.similarity_matrix != partial_matrix, formatted_matrix(matcher)


def formatted_matrix(matcher: ObjectListMatcher) -> str:
    lines = ["<Similarity Matrix"]
    for b_similarities in matcher.similarity_matrix:
        l = ""
        for b_sim in b_similarities:
            l += f"{b_sim:1.4f}  "
        lines.append(l)
    return "\n".join(lines) + "\n>"


class TMatchClassFields(TestCase):
    def test_matching_works(self):
        a, b = self._get_car_lists()

        attr_to_weight = {(lambda c: c.seats): 4, (lambda c: c.name): 1,
                          (lambda c: c.features): 5}
        matcher = ObjectListMatcher(attr_to_weight)

        assert matcher.get_indices(a, b) == [2, None, 1, 0]

    def _get_car_lists(self):
        a = [Car(1, "Speedy", ["gps", "heater"]), Car(2, "Cheaporghiny", []),
             Car(16, "Half-a-Bus", ["buttons"]), Car(5, "Normal Model 1", ["music"])]
        b = [Car(3, "Mödel V5", ["gps"]), Car(19, "Cyberbus", ["buttons"]),
             Car(2, "Sheeporghiny", ["gps", "heater", "sheep sound button"])]
        return a, b

    def test_dominating_name_weights(self):
        a, b = self._get_car_lists()
        attr_to_weight = {(lambda c: c.seats): 0.5, (lambda c: c.name): 9,
                          (lambda c: c.features): 1.2}

        matcher = ObjectListMatcher(attr_to_weight)

        assert matcher.get_indices(a, b) == [None, 2, 1, 0]

    def test_minimum_similarity(self):
        a, b = self._get_car_lists()

        attr_to_weight = {(lambda c: c.seats): 3, (lambda c: c.features): 8}
        matcher = ObjectListMatcher(attr_to_weight)
        matcher.should_store_similarity_matrix = True

        assert matcher.get_indices(a, b) == [2, 0, 1, None], formatted_matrix(matcher)

        matcher.minimum_similarity_ratio = 0.71
        assert matcher.get_indices(a, b) == [2, None, 1, None], formatted_matrix(
            matcher)

        matcher.minimum_similarity_ratio = 0.9
        assert matcher.get_indices(a, b) == [None, None, 1, None], formatted_matrix(
            matcher)


@dataclass
class Car:
    seats: int
    name: str
    features: list[str]
