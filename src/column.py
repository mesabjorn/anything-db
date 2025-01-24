class Column:
    def __init__(self, name: str, _type: str, not_null: bool = False):
        self.name = name
        self.type = _type
        self.not_null = not_null == 1
        self.primary_key = False
        self.visible = self.name != "updated" and name != "id"

    def enter(self, isupdate=False):
        while True:
            value = input(f"Value for {self.name}: ({self.type})").strip()
            if isupdate or (len(value) > 0 and self.not_null) or not self.not_null:
                return value

            logger.warning(
                f"A value for '{self.name}' is required and cannot be empty."
            )

    def __str__(self):
        return (
            f"<Column {self.name}:{self.type} {'!REQUIRED!' if self.not_null else ''}>"
        )
