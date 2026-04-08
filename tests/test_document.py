"""Tests for pathy_svg.document module."""

import pytest

from pathy_svg.document import SVGDocument
from pathy_svg.exceptions import PathNotFoundError, SVGParseError
from pathy_svg.transform import ViewBox


class TestConstruction:
    def test_from_file(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        assert doc.root is not None

    def test_from_string(self, simple_svg_string):
        doc = SVGDocument.from_string(simple_svg_string)
        assert doc.root is not None

    def test_from_string_bytes(self, simple_svg_string):
        doc = SVGDocument.from_string(simple_svg_string.encode("utf-8"))
        assert doc.root is not None

    def test_from_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            SVGDocument.from_file("/nonexistent/path.svg")

    def test_from_string_malformed(self):
        with pytest.raises(SVGParseError):
            SVGDocument.from_string("<not valid xml><<<")

    def test_from_minimal(self, minimal_svg_string):
        doc = SVGDocument.from_string(minimal_svg_string)
        assert "p1" in doc.path_ids


class TestProperties:
    def test_path_ids(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        ids = doc.path_ids
        assert set(ids) == {"stomach", "liver", "heart", "lung_l", "lung_r"}

    def test_group_ids(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        ids = doc.group_ids
        assert "organs" in ids
        assert "outline" in ids

    def test_element_ids(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        ids = doc.element_ids
        # Should include paths, groups, and the border rect
        assert "stomach" in ids
        assert "organs" in ids
        assert "border" in ids

    def test_viewbox(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        assert doc.viewbox == ViewBox(0, 0, 500, 400)

    def test_viewbox_none(self):
        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg"><path id="p" d="M 0 0 L 1 1"/></svg>'
        )
        assert doc.viewbox is None

    def test_dimensions(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        w, h = doc.dimensions
        assert w == 500
        assert h == 400

    def test_namespaces(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        ns = doc.namespaces
        assert "http://www.w3.org/2000/svg" in ns.values()

    def test_metadata(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        meta = doc.metadata
        assert meta["title"] == "Simple Test SVG"
        assert meta["desc"] is not None


class TestImmutability:
    def test_clone_is_independent(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        clone = doc._clone()

        # Modify the clone
        elem = clone._find_by_id("stomach")
        elem.set("fill", "#ff0000")

        # Original should be unchanged
        orig_elem = doc._find_by_id("stomach")
        assert orig_elem.get("fill") == "#ffffff"

    def test_clone_preserves_data(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        clone = doc._clone()
        assert clone.path_ids == doc.path_ids
        assert clone.viewbox == doc.viewbox


class TestSerialization:
    def test_to_string_roundtrip(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        svg_str = doc.to_string()
        doc2 = SVGDocument.from_string(svg_str)
        assert doc2.path_ids == doc.path_ids

    def test_to_bytes(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        data = doc.to_bytes()
        assert isinstance(data, bytes)
        assert b"<svg" in data

    def test_save(self, simple_svg_path, tmp_path):
        doc = SVGDocument.from_file(simple_svg_path)
        out = tmp_path / "output.svg"
        doc.save(out)
        assert out.exists()
        doc2 = SVGDocument.from_file(out)
        assert doc2.path_ids == doc.path_ids

    def test_repr_svg(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        svg = doc._repr_svg_()
        assert isinstance(svg, str)
        assert "<svg" in svg


class TestElementLookup:
    def test_find_by_id(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        elem = doc._find_by_id("stomach")
        assert elem is not None
        assert elem.get("id") == "stomach"

    def test_find_by_id_missing(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        assert doc._find_by_id("nonexistent") is None


class TestGeometricQueries:
    def test_bbox(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        box = doc.bbox("liver")
        assert box.x == pytest.approx(200)
        assert box.y == pytest.approx(100)
        assert box.width == pytest.approx(80)
        assert box.height == pytest.approx(80)

    def test_centroid(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        cx, cy = doc.centroid("liver")
        assert cx == pytest.approx(240)
        assert cy == pytest.approx(140)

    def test_bbox_missing_id(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        with pytest.raises(PathNotFoundError):
            doc.bbox("nonexistent")


class TestStyledSVG:
    def test_path_ids(self, styled_svg_path):
        doc = SVGDocument.from_file(styled_svg_path)
        assert set(doc.path_ids) == {"region_a", "region_b", "region_c"}


class TestGroupedSVG:
    def test_group_ids(self, grouped_svg_path):
        doc = SVGDocument.from_file(grouped_svg_path)
        ids = doc.group_ids
        assert "north" in ids
        assert "south" in ids
        assert "layer_bg" in ids
        assert "layer_regions" in ids

    def test_nested_path_ids(self, grouped_svg_path):
        doc = SVGDocument.from_file(grouped_svg_path)
        ids = doc.path_ids
        assert set(ids) == {"north_a", "north_b", "south_a", "south_b"}


class TestDataFrameIntegration:
    """Tests for Pandas DataFrame integration."""

    def test_from_dataframe(self, simple_svg_path):
        pd = pytest.importorskip("pandas")
        df = pd.DataFrame(
            {
                "id": ["stomach", "liver", "heart"],
                "value": [1.0, 2.0, 3.0],
            }
        )
        doc, data = SVGDocument.from_dataframe(
            simple_svg_path, df, id_col="id", value_col="value"
        )
        assert isinstance(doc, SVGDocument)
        assert data == {"stomach": 1.0, "liver": 2.0, "heart": 3.0}

    def test_from_dataframe_missing_columns(self, simple_svg_path):
        pd = pytest.importorskip("pandas")
        df = pd.DataFrame({"x": [1], "y": [2]})
        with pytest.raises(ValueError, match="Column 'id' not found"):
            SVGDocument.from_dataframe(
                simple_svg_path, df, id_col="id", value_col="value"
            )

    def test_from_dataframe_missing_value_column(self, simple_svg_path):
        pd = pytest.importorskip("pandas")
        df = pd.DataFrame({"id": ["a"], "other": [1]})
        with pytest.raises(ValueError, match="Column 'value' not found"):
            SVGDocument.from_dataframe(
                simple_svg_path, df, id_col="id", value_col="value"
            )

    def test_heatmap_from_dataframe(self, simple_svg_path):
        pd = pytest.importorskip("pandas")
        doc = SVGDocument.from_file(simple_svg_path)
        df = pd.DataFrame(
            {
                "id": ["stomach", "liver", "heart", "lung_l", "lung_r"],
                "value": [10, 20, 30, 40, 50],
            }
        )
        result = doc.heatmap_from_dataframe(df, id_col="id", value_col="value")
        assert isinstance(result, SVGDocument)
        # Verify colors were applied (fill should be set on elements)
        stomach = result._find_by_id("stomach")
        assert stomach.get("style") is not None
        assert "fill:" in stomach.get("style")

    def test_heatmap_from_dataframe_with_options(self, simple_svg_path):
        pd = pytest.importorskip("pandas")
        doc = SVGDocument.from_file(simple_svg_path)
        df = pd.DataFrame(
            {
                "id": ["stomach", "liver"],
                "value": [0.5, 0.9],
            }
        )
        result = doc.heatmap_from_dataframe(
            df, id_col="id", value_col="value", palette="viridis", vmin=0, vmax=1
        )
        assert isinstance(result, SVGDocument)

    def test_data_from_dataframe_static_method(self, simple_svg_path):
        pd = pytest.importorskip("pandas")
        doc = SVGDocument.from_file(simple_svg_path)
        df = pd.DataFrame(
            {
                "region": ["a", "b", "c"],
                "temp": [10.5, 20.5, 30.5],
            }
        )
        data = doc._data_from_dataframe(df, id_col="region", value_col="temp")
        assert data == {"a": 10.5, "b": 20.5, "c": 30.5}

    def test_data_from_dataframe_skips_invalid_values(self, simple_svg_path):
        pd = pytest.importorskip("pandas")
        df = pd.DataFrame(
            {
                "id": ["a", "b", "c"],
                "value": [1.0, "not_a_number", 3.0],
            }
        )
        doc = SVGDocument.from_file(simple_svg_path)
        data = doc._data_from_dataframe(df, id_col="id", value_col="value")
        assert data == {"a": 1.0, "c": 3.0}
