from scheduler import *


def strategy0():
    scheduler = Scheduler(
        config_dir="configs",
        arrange="arrange1",
        resource=Resource(2, 61000, 6000, 100),
    )

    counters = Counters(5, 42, 1, 5, False, True)

    scheduler.schedule(
        [0], check_in=False, init_counters=counters, resource_increment=Resource()
    )
    scheduler.schedule([DOSSIER, OPRT])
    scheduler.schedule([DOSSIER])
    scheduler.schedule([DOSSIER, UP_OPRT], use_origeometry=True)
    scheduler.schedule([DOSSIER, OPRT])

    # scheduler.simulate()
    scheduler.evaluate(scale=5000, workers=16)


def strategy1():
    scheduler = Scheduler(
        config_dir="configs",
        arrange="arrange1",
        resource=Resource(2, 61000, 6000, 100),
    )

    counters = Counters(5, 42, 1, 5, False, True)

    scheduler.schedule(
        [0], check_in=False, init_counters=counters, resource_increment=Resource()
    )
    scheduler.schedule([URGENT])
    scheduler.schedule([URGENT])
    scheduler.schedule(
        [[DOSSIER, GT ^ 43, UP_OPRT], [URGENT, LE ^ 43, UP_OPRT]], use_origeometry=True
    )
    scheduler.schedule([URGENT])

    # scheduler.simulate()
    scheduler.evaluate(scale=5000, workers=16)


def strategy2():
    scheduler = Scheduler(
        config_dir="configs",
        arrange="arrange1",
        resource=Resource(2, 61000, 6000, 100),
    )

    counters = Counters(5, 42, 1, 5, False, True)

    scheduler.schedule(
        [0], check_in=False, init_counters=counters, resource_increment=Resource()
    )
    scheduler.schedule([DOSSIER, OPRT])
    scheduler.schedule([DOSSIER, [URGENT, LE ^ 43, UP_OPRT]])
    scheduler.schedule([DOSSIER, UP_OPRT], use_origeometry=True)
    scheduler.schedule([DOSSIER, [URGENT, LE ^ 43, UP_OPRT]])

    # scheduler.simulate()
    scheduler.evaluate(scale=5000, workers=16)


def strategy3():
    scheduler = Scheduler(
        config_dir="configs",
        arrange="arrange1",
        resource=Resource(2, 61000, 6000, 100),
    )

    counters = Counters(5, 42, 1, 5, False, True)

    scheduler.schedule(
        [0], check_in=False, init_counters=counters, resource_increment=Resource()
    )
    scheduler.schedule([OPRT])
    scheduler.schedule([OPRT])
    scheduler.schedule([UP_OPRT], use_origeometry=True)
    scheduler.schedule([OPRT])

    # scheduler.simulate()
    scheduler.evaluate(scale=5000, workers=16)


def strategy4():
    scheduler = Scheduler(
        config_dir="configs",
        arrange="arrange1",
        resource=Resource(2, 61000, 6000, 100),
    )

    counters = Counters(5, 42, 1, 5, False, True)

    scheduler.schedule(
        [0], check_in=False, init_counters=counters, resource_increment=Resource()
    )
    scheduler.schedule([0])
    scheduler.schedule([0])
    scheduler.schedule([POTENTIAL ^ 3], use_origeometry=True)
    scheduler.schedule([0])

    # scheduler.simulate()
    scheduler.evaluate(scale=5000, workers=16)


if __name__ == "__main__":
    strategy0()
    strategy1()
    strategy2()
    strategy3()
    strategy4()
