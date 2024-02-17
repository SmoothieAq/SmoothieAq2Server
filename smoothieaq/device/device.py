from .observable import *


class Device:

    def __init__(self) -> None:
        self.m_device: Optional[aqt.Device] = None
        self.id: Optional[str] = None
        self.status_id: Optional[str] = None
        self.driver: Optional[Driver] = None
        self.rx_status_observable: Optional[rx.Observable[ObservableEmit]] = None
        self.observables: Optional[dict[str, Observable]] = None
        self.paused: bool = False
        self._rx_paused = rx.subject.BehaviorSubject[bool](self.paused)
        self._rx_all_subject = rx.Subject[rx.Observable[ObservableEmit]]()
        self.rx_all_observables: Optional[rx.Observable[ObservableEmit]] = None

    def pause(self, paused: bool = True) -> None:
        self.paused = paused
        self._rx_paused.on_next(paused)
        for o in self.observables.values():
            o.pause(paused)
        if paused:
            self.stop()
        else:
            self.start()

    def unpause(self) -> None:
        self.pause(False)

    def init(self, m_device: aqt.Device) -> 'Device':
        self.m_device: aqt.Device = m_device
        self.id: str = m_device.id
        self.status_id = self.id + '?'

        if self.m_device.enabled is not False:
            s: rx.Observable[RawEmit]
            if m_device.driver and m_device.driver.id:
                self.driver = driver_init(m_device.driver)
                s = self.driver.rx_status_observable
            else:
                s = rx.of(RawEmit(enumValue=DriverStatus.RUNNING))

            def status(t: tuple[bool, RawEmit]) -> ObservableEmit:
                (paused, driver_status) = t
                # print("dev stat",self.id, paused,driver_status)
                if paused:
                    return emit_enum_value(self.status_id, Status.PAUSED)
                elif driver_status.enumValue in {DriverStatus.RUNNING, DriverStatus.PROGRAM_RUNNING,
                                                 DriverStatus.SCHEDULE_RUNNING}:
                    return emit_enum_value(self.status_id, Status.RUNNING)
                elif driver_status.enumValue in {DriverStatus.IN_ERROR, DriverStatus.CLOSING}:
                    return emit_enum_value(self.status_id, Status.ERROR)
                else:
                    return emit_enum_value(self.status_id, Status.INITIALIZING)

            self.rx_status_observable = rx.combine_latest(self._rx_paused, s).pipe(
                op.map(status),
                op.distinct_until_changed(lambda e: e.enumValue)
            )
        else:
            self.rx_status_observable = rx.of(emit_enum_value(self.status_id, Status.DISABLED))

        def create_observable(mo: aqt.Observable) -> tuple[str, Observable]:
            o: Observable
            if isinstance(mo, aqt.Measure):
                o = Measure()
            elif isinstance(mo, aqt.Amount):
                o = Amount()
            elif isinstance(mo, aqt.State):
                o = State()
            elif isinstance(mo, aqt.Event):
                o = Event()
            else:
                raise Exception("")
            return mo.id, o.init(mo, self)

        self.observables = dict(map(create_observable, m_device.observables or []))

        self.rx_all_observables = rx.from_list(([self.rx_status_observable] +
                                                [o for ob in self.observables.values() for o in
                                                 [ob.rx_observable, ob.rx_status_observable]])).pipe(
            op.merge_all()
        )

        return self

    def start(self) -> None:
        assert self.m_device.enabled is not False
        if self.driver:
            self.driver.start()
        for o in self.observables.values():
            o.start()

    def stop(self) -> None:
        for o in self.observables.values():
            o.stop()
        if self.driver:
            self.driver.stop()

    def close(self) -> None:
        for o in self.observables.values():
            o.close()
        self._rx_paused.on_completed()
