from packet_runner import config as C
from packet_runner.bonus import BonusLetters


def test_letters_in_order_and_bonus_once():
    b = BonusLetters()
    t = C.LETTER_FIRST
    for i, ch in enumerate(C.BONUS_WORD):
        assert b.due(t) and b.next_letter == ch
        b.spawned(t)
        assert not b.due(t + 100)                        # 화면에 글자가 있는 동안은 다음 글자 없음
        started = b.collect()
        assert started == (i == len(C.BONUS_WORD) - 1)
        t += C.LETTER_EVERY
    assert b.in_bonus and b.done
    b.update(C.BONUS_TIME)
    assert not b.in_bonus
    assert not b.due(t + 1000)                          # 한 판에 한 번


def test_missed_letter_comes_back_later():
    b = BonusLetters()
    b.spawned(C.LETTER_FIRST)
    b.missed()
    assert not b.due(C.LETTER_FIRST + 1)                 # 바로 다시 나오지는 않음
    assert b.due(C.LETTER_FIRST + C.LETTER_EVERY)
    assert b.next_letter == C.BONUS_WORD[0]              # 같은 글자부터 다시


def test_no_letter_before_first_time():
    assert not BonusLetters().due(C.LETTER_FIRST - 0.1)
