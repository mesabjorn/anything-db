import time
from src.column import Column


class Schema:
    def __init__(self, name: str, columns: list[tuple]):
        self.name = name
        self.columns = [Column(name=c[1], _type=c[2], not_null=c[3]) for c in columns]

    def has_changed(self) -> bool:
        # returns whether or not this table has an update column named 'updated'
        return len([x.name == "updated" for x in self.columns]) > 0

    def enter_values(self) -> dict[str, str]:
        updates = {}
        for c in self.columns:
            if c.visible:
                updates[c.name] = c.enter()

        if self.has_changed():
            updates["updated"] = time.time()
        return updates

    def re_enter_values(self) -> dict[str, str]:
        updates = {}
        for c in self.columns:
            if c.visible:
                updates[c.name] = c.enter(isupdate=True)

        if self.has_changed():
            updates["updated"] = time.time()
        return updates

    def _get_column(self, name: str):
        return next((c for c in self.columns if c.name == name), None)

    @property
    def column(self):
        return self._get_column

    def __str__(self):
        print(f"Schema for table '{self.name}':")
        for column in filter(lambda x: x.visible, self.columns):
            print(f"\t{column}")
        return ""
