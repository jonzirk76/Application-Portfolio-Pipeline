from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Text = Annotated[str, Field(min_length=1, max_length=200)]
Positive = Annotated[float, Field(gt=0, allow_inf_nan=False)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BomLine(StrictModel):
    id: Text
    component_guid: Annotated[str, Field(pattern=r"^[0-3][0-9A-Za-z_$]{21}$")]
    tag: Text
    specification: Text
    length_m: Positive
    count: Literal[1]  # One cut member per BOM line in this pilot.


class PoLine(StrictModel):
    id: Text
    po: Text
    bom_line_id: Text
    specification: Text
    length_m: Positive
    count: Literal[1]
    status: Literal["ordered"]


class Procurement(StrictModel):
    synthetic: Literal[True]
    bom_revision: Text
    bom_lines: Annotated[list[BomLine], Field(max_length=2000)]
    po_lines: Annotated[list[PoLine], Field(max_length=2000)]

    @model_validator(mode="after")
    def unique_ids_and_links(self):
        for lines in (self.bom_lines, self.po_lines):
            if len({line.id for line in lines}) != len(lines):
                raise ValueError("BOM/PO line identifiers must be unique")
        bom_ids = {line.id for line in self.bom_lines}
        if len({line.component_guid for line in self.bom_lines}) != len(self.bom_lines):
            raise ValueError("This pilot permits one BOM line per component")
        if any(line.bom_line_id not in bom_ids for line in self.po_lines):
            raise ValueError("Every PO line must reference a supplied BOM line")
        return self


class AuditRequest(StrictModel):
    baseline_id: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    revised_id: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    procurement_id: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
