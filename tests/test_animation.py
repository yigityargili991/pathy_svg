"""Tests for pathy_svg.animation module."""

from fractions import Fraction

import pytest
from lxml import etree

from pathy_svg.animation import inject_animation
from pathy_svg.document import SVGDocument


class TestAnimate:
    def test_pulse(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.heatmap({"stomach": 0.5}).animate(effect="pulse")
        svg_str = result.to_string()
        assert "@keyframes" in svg_str
        assert "pathy-pulse" in svg_str

    def test_fade_in(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.animate(effect="fade_in")
        svg_str = result.to_string()
        assert "pathy-fade" in svg_str

    def test_blink(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.animate(effect="blink", duration=1.0)
        svg_str = result.to_string()
        assert "pathy-blink" in svg_str

    def test_sequential(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.animate(effect="sequential", duration=3.0)
        svg_str = result.to_string()
        assert "pathy-seq" in svg_str
        assert 'id="stomach"' in svg_str
        assert "animation-delay: 0.00s" in svg_str

    def test_sequential_accepts_explicit_order(self):
        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<path id="a"/><rect id="b"/><circle id="c"/>'
            "</svg>"
        )
        result = doc.animate(
            effect="sequential", duration=2.0, data_order=("c", "a")
        )
        css = result.root.find(".//{http://www.w3.org/2000/svg}style").text
        assert css.index('id="c"') < css.index('id="a"')
        assert 'id="b"' not in css
        assert "animation-delay: 0.00s" in css
        assert "animation-delay: 1.00s" in css

    def test_sequential_skips_elements_without_ids(self):
        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<path/><rect id="identified"/><circle/>'
            "</svg>"
        )
        result = doc.animate(effect="sequential")
        css = result.root.find(".//{http://www.w3.org/2000/svg}style").text
        assert css.count("animation-delay:") == 1
        assert 'id="identified"' in css
        assert "[id=\"None\"]" not in css

    def test_sequential_with_no_identifiable_elements(self):
        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg"><path/><rect/></svg>'
        )
        result = doc.animate(effect="sequential")
        css = result.root.find(".//{http://www.w3.org/2000/svg}style").text
        assert "@keyframes pathy-seq" in css
        assert "animation-delay:" not in css
        assert "path, rect" not in css

    def test_immutability(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.animate(effect="pulse")
        assert "@keyframes" not in doc.to_string()
        assert "@keyframes" in result.to_string()

    def test_invalid_effect(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        with pytest.raises(ValueError):
            doc.animate(effect="nonexistent")

    @pytest.mark.parametrize("duration", [0, -1, float("inf"), float("nan")])
    def test_invalid_duration(self, simple_svg_path, duration):
        doc = SVGDocument.from_file(simple_svg_path)
        with pytest.raises(ValueError, match="duration"):
            doc.animate(duration=duration)

    def test_non_numeric_duration(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        with pytest.raises(TypeError, match="duration"):
            doc.animate(duration=True)

    def test_repeat_animation_replaces_generated_style(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.animate(effect="pulse").animate(effect="blink")
        svg_str = result.to_string()
        assert svg_str.count('data-pathy-animation="true"') == 1
        assert "pathy-pulse" not in svg_str
        assert "pathy-blink" in svg_str


class TestInjectAnimationDirect:
    def _make_tree(self):
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
            '<path id="a" d="M 0 0 L 10 10"/>'
            '<path id="b" d="M 0 0 L 20 20"/>'
            '<path id="c" d="M 0 0 L 30 30"/>'
            "</svg>"
        )
        return etree.ElementTree(etree.fromstring(svg.encode()))

    def test_sequential_with_data_order(self):
        tree = self._make_tree()
        inject_animation(tree, effect="sequential", data_order=["a", "b", "c"])
        style = tree.getroot().find(".//{http://www.w3.org/2000/svg}style")
        assert style is not None
        css = style.text
        assert "pathy-seq" in css
        assert 'id="a"' in css
        assert 'id="b"' in css
        assert 'id="c"' in css
        assert "animation-delay:" in css

    def test_sequential_with_data_order_no_loop(self):
        tree = self._make_tree()
        inject_animation(tree, effect="sequential", data_order=["a", "b"], loop=False)
        style = tree.getroot().find(".//{http://www.w3.org/2000/svg}style")
        css = style.text
        assert "animation-delay:" in css
        keyframe_name = style.xpath("string(@*[local-name()='keyframe'])")
        assert f"animation: {keyframe_name} 2.0s ease-in 1;" in css
        assert css.count("animation-fill-mode: backwards;") == 2
        assert "infinite" not in css

    def test_finite_sequential_restores_original_opacity(self):
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<path id="dim" opacity=".25"/>'
            "</svg>"
        )
        tree = etree.ElementTree(etree.fromstring(svg.encode()))

        inject_animation(tree, effect="sequential", loop=False)

        path = tree.getroot().find("{http://www.w3.org/2000/svg}path")
        style = tree.getroot().find(".//{http://www.w3.org/2000/svg}style")
        rule = next(line for line in style.text.splitlines() if 'id="dim"' in line)
        assert path.get("opacity") == ".25"
        assert "animation-fill-mode: backwards;" in rule
        assert "opacity:" not in rule

    def test_sequential_without_data_order(self):
        tree = self._make_tree()
        inject_animation(tree, effect="sequential", data_order=None)
        style = tree.getroot().find(".//{http://www.w3.org/2000/svg}style")
        assert style is not None
        assert "pathy-seq" in style.text
        assert style.text.index('id="a"') < style.text.index('id="b"')
        assert style.text.index('id="b"') < style.text.index('id="c"')
        assert "animation-delay: 0.00s" in style.text
        assert "animation-delay: 0.67s" in style.text
        assert "animation-delay: 1.33s" in style.text

    def test_sequential_escapes_ids_in_css_selector(self):
        tree = self._make_tree()
        dangerous_id = 'a"] { color: red; } /*'
        inject_animation(tree, effect="sequential", data_order=[dangerous_id])
        style = tree.getroot().find(".//{http://www.w3.org/2000/svg}style")
        assert dangerous_id not in style.text
        assert "\\22 " in style.text
        assert "\\5d " in style.text

    def test_sequential_discovery_skips_definition_geometry(self):
        svg = """<svg xmlns="http://www.w3.org/2000/svg">
          <defs>
            <path id="in-defs"/>
            <symbol id="icon"><rect id="in-symbol"/></symbol>
          </defs>
          <clipPath id="clip"><circle id="in-clip"/></clipPath>
          <mask id="mask"><ellipse id="in-mask"/></mask>
          <pattern id="pattern"><polygon id="in-pattern"/></pattern>
          <marker id="marker"><polyline id="in-marker"/></marker>
          <linearGradient id="gradient"><path id="in-gradient"/></linearGradient>
          <filter id="filter"><rect id="in-filter"/></filter>
          <path id="visible-a"/>
          <use id="visible-use" href="#icon"/>
          <rect id="visible-b"/>
        </svg>"""
        tree = etree.ElementTree(etree.fromstring(svg.encode()))

        inject_animation(tree, effect="sequential", duration=2.0)

        style = tree.getroot().find(".//{http://www.w3.org/2000/svg}style")
        css = style.text
        assert css.count("animation-delay:") == 2
        assert 'id="visible-a"' in css
        assert 'id="visible-b"' in css
        assert 'id="visible-use"' not in css
        assert "animation-delay: 0.00s" in css
        assert "animation-delay: 1.00s" in css
        for definition_id in (
            "in-defs",
            "in-symbol",
            "in-clip",
            "in-mask",
            "in-pattern",
            "in-marker",
            "in-gradient",
            "in-filter",
        ):
            assert f'id="{definition_id}"' not in css

    @pytest.mark.parametrize("effect", ["pulse", "fade_in", "blink", "sequential"])
    def test_duration_is_serialized_from_normalized_number(self, effect):
        tree = self._make_tree()
        inject_animation(tree, effect=effect, duration=Fraction(1, 2))
        style = tree.getroot().find(".//{http://www.w3.org/2000/svg}style")
        assert "0.5s" in style.text
        assert "1/2s" not in style.text

    @pytest.mark.parametrize("effect", ["pulse", "fade_in", "blink"])
    def test_non_sequential_effects_target_only_rendered_geometry(self, effect):
        svg = """<svg xmlns="http://www.w3.org/2000/svg">
          <defs>
            <path id="in-defs" class="resource"/>
            <symbol id="icon"><rect id="in-symbol"/></symbol>
          </defs>
          <clipPath id="clip"><circle id="in-clip"/></clipPath>
          <mask id="mask"><ellipse id="in-mask"/></mask>
          <pattern id="pattern"><polygon id="in-pattern"/></pattern>
          <marker id="marker"><polyline id="in-marker"/></marker>
          <path id="visible" class="kept alpha"/>
          <rect class="no-id"/>
        </svg>"""
        tree = etree.ElementTree(etree.fromstring(svg.encode()))

        inject_animation(tree, effect=effect)

        root = tree.getroot()
        style = root.find(".//{http://www.w3.org/2000/svg}style")
        target_class = style.get("data-pathy-animation-class")
        visible = root.xpath('//*[@id="visible"]')[0]
        no_id = root.xpath('./*[local-name()="rect"]')[0]
        assert target_class
        assert f".{target_class} {{" in style.text
        assert visible.get("class") == f"kept alpha {target_class}"
        assert no_id.get("class") == f"no-id {target_class}"
        assert root.xpath('//*[@id="in-defs"]')[0].get("class") == "resource"
        for resource_id in (
            "in-defs",
            "in-symbol",
            "in-clip",
            "in-mask",
            "in-pattern",
            "in-marker",
        ):
            resource = root.xpath(f'//*[@id="{resource_id}"]')[0]
            assert target_class not in (resource.get("class") or "").split()

    def test_generated_target_class_preserves_classes_and_is_idempotent(self):
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<path id="visible" class="pathy-animation-target kept"/>'
            "</svg>"
        )
        tree = etree.ElementTree(etree.fromstring(svg.encode()))

        inject_animation(tree, effect="pulse")
        inject_animation(tree, effect="blink")

        root = tree.getroot()
        path = root.find("{http://www.w3.org/2000/svg}path")
        styles = root.findall(".//{http://www.w3.org/2000/svg}style")
        target_class = styles[0].get("data-pathy-animation-class")
        assert len(styles) == 1
        assert target_class == "pathy-animation-target-2"
        assert path.get("class") == "pathy-animation-target kept " + target_class
        assert path.get("class").split().count(target_class) == 1
        assert "pathy-pulse" not in styles[0].text
        assert "pathy-blink" in styles[0].text

    @pytest.mark.parametrize(
        ("effect", "user_keyframe"),
        [
            ("pulse", "pathy-pulse"),
            ("fade_in", "pathy-fade"),
            ("blink", "pathy-blink"),
            ("sequential", "pathy-seq"),
        ],
    )
    def test_generated_keyframe_name_avoids_user_collision_and_is_stable(
        self, effect, user_keyframe
    ):
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg"><defs><style>'
            f"@keyframes {user_keyframe} {{ from {{ opacity: .2; }} }}"
            "</style></defs><path id=\"visible\"/></svg>"
        )
        tree = etree.ElementTree(etree.fromstring(svg.encode()))

        inject_animation(tree, effect=effect)
        first_styles = tree.getroot().findall(
            ".//{http://www.w3.org/2000/svg}style"
        )
        first_generated = next(
            style
            for style in first_styles
            if style.xpath("string(@*[local-name()='keyframe'])")
        )
        first_name = first_generated.xpath("string(@*[local-name()='keyframe'])")

        inject_animation(tree, effect=effect)
        second_styles = tree.getroot().findall(
            ".//{http://www.w3.org/2000/svg}style"
        )
        second_generated = next(
            style
            for style in second_styles
            if style.xpath("string(@*[local-name()='keyframe'])")
        )
        second_name = second_generated.xpath("string(@*[local-name()='keyframe'])")

        assert first_name != user_keyframe
        assert first_name == second_name
        assert f"@keyframes {first_name} " in second_generated.text
        assert f"animation: {first_name} " in second_generated.text
        assert len(second_styles) == 2
        assert f"@keyframes {user_keyframe} " in second_styles[0].text

    def test_spoofed_public_markers_and_user_classes_survive_replacement(self):
        svg = """<svg xmlns="http://www.w3.org/2000/svg">
          <defs><style data-pathy-animation="true"
            data-pathy-animation-class="user-marker">
            @keyframes user-marker { from { opacity: .5; } }
            .user-marker { animation: user-marker 1s; }
          </style></defs>
          <path id="visible" class="user-marker pathy-animation-target kept"/>
        </svg>"""
        tree = etree.ElementTree(etree.fromstring(svg.encode()))

        inject_animation(tree, effect="pulse")
        inject_animation(tree, effect="blink")

        root = tree.getroot()
        styles = root.findall(".//{http://www.w3.org/2000/svg}style")
        path = root.find("{http://www.w3.org/2000/svg}path")
        generated = [
            style
            for style in styles
            if style.xpath("string(@*[local-name()='provenance'])")
            == "pathy-generated-animation-v1"
        ]
        assert len(styles) == 2
        assert len(generated) == 1
        assert "@keyframes user-marker" in styles[0].text
        assert styles[0].get("data-pathy-animation-class") == "user-marker"
        assert path.get("class").startswith(
            "user-marker pathy-animation-target kept "
        )
        assert path.get("class").split().count("user-marker") == 1
        assert path.get("class").split().count("pathy-animation-target") == 1
        assert generated[0].get("data-pathy-animation-class") == (
            "pathy-animation-target-2"
        )

    @pytest.mark.parametrize("suffix", [9, 10, 19, 20, 100])
    def test_generated_class_and_marker_suffix_boundaries_are_cleaned(self, suffix):
        private_ns = "urn:pathy-svg:private:animation:v1"
        occupied_classes = ["pathy-animation-target"] + [
            f"pathy-animation-target-{number}" for number in range(2, suffix)
        ]
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg">'
            f'<path id="visible" class="{" ".join(occupied_classes)} kept"/>'
            "</svg>"
        )
        tree = etree.ElementTree(etree.fromstring(svg.encode()))
        root = tree.getroot()
        for number in range(1, suffix):
            marker_name = "class-owner" if number == 1 else f"class-owner-{number}"
            root.set(f"{{{private_ns}}}{marker_name}", "user-spoof")

        inject_animation(tree, effect="pulse")
        inject_animation(tree, effect="blink")

        path = root.find("{http://www.w3.org/2000/svg}path")
        styles = root.findall(".//{http://www.w3.org/2000/svg}style")
        owned = [
            style
            for style in styles
            if style.xpath("string(@*[local-name()='provenance'])")
            == "pathy-generated-animation-v1"
        ]
        generated_class = f"pathy-animation-target-{suffix}"
        assert len(owned) == 1
        assert owned[0].get("data-pathy-animation-class") == generated_class
        assert owned[0].xpath("string(@*[local-name()='class-marker'])") == (
            f"class-owner-{suffix}"
        )
        assert path.get("class").split().count(generated_class) == 1
        assert path.get("class").split()[-2:] == ["kept", generated_class]
        assert path.xpath(
            f"string(@*[namespace-uri()='{private_ns}' "
            f"and local-name()='class-owner-{suffix}'])"
        ) == generated_class
        for number in range(1, suffix):
            marker_name = "class-owner" if number == 1 else f"class-owner-{number}"
            assert root.get(f"{{{private_ns}}}{marker_name}") == "user-spoof"

    def test_pulse_no_loop(self):
        tree = self._make_tree()
        inject_animation(tree, effect="pulse", loop=False, duration=3.0)
        style = tree.getroot().find(".//{http://www.w3.org/2000/svg}style")
        css = style.text
        assert "3.0s" in css
        assert "1;" in css  # not infinite

    def test_creates_defs_if_missing(self):
        svg = '<svg xmlns="http://www.w3.org/2000/svg"><path id="x" d="M 0 0"/></svg>'
        tree = etree.ElementTree(etree.fromstring(svg.encode()))
        defs_before = tree.getroot().find("{http://www.w3.org/2000/svg}defs")
        assert defs_before is None
        inject_animation(tree, effect="pulse")
        defs_after = tree.getroot().find("{http://www.w3.org/2000/svg}defs")
        assert defs_after is not None

    def test_invalid_effect_raises(self):
        tree = self._make_tree()
        with pytest.raises(ValueError, match="Unknown animation effect"):
            inject_animation(tree, effect="spin")

    def test_invalid_data_order_does_not_modify_tree(self):
        tree = self._make_tree()
        before = etree.tostring(tree)
        with pytest.raises(TypeError, match="data_order"):
            inject_animation(tree, effect="sequential", data_order="abc")
        assert etree.tostring(tree) == before

    @pytest.mark.parametrize("loop", [0, 1, "yes", None])
    def test_invalid_loop_does_not_modify_tree(self, loop):
        tree = self._make_tree()
        before = etree.tostring(tree)
        with pytest.raises(TypeError, match="loop"):
            inject_animation(tree, loop=loop)
        assert etree.tostring(tree) == before

    def test_overflowing_duration_does_not_modify_tree(self):
        tree = self._make_tree()
        before = etree.tostring(tree)
        huge_duration = Fraction(10**10_000, 1)
        with pytest.raises(ValueError, match="finite number greater than 0"):
            inject_animation(tree, duration=huge_duration)
        assert etree.tostring(tree) == before
