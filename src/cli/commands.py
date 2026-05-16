from __future__ import annotations

from dataclasses import dataclass
from typing import IO, Protocol

from src.adapters.file_validator import FileVideoValidator
from src.domain.faults import LiftPhase
from src.domain.knowledge_base import KnowledgeBase
from src.use_cases.analyze_video import AnalyzeVideoResult


class _UseCase(Protocol):
    def execute(self, input_path: str, output_path: str) -> str | AnalyzeVideoResult: ...


class _CompareUseCase(Protocol):
    def execute(self, left_path: str, right_path: str, output_path: str) -> str: ...


@dataclass
class LiftsCommand:
    kb: KnowledgeBase
    out: IO[str]

    def run(self) -> int:
        lifts = self.kb.lifts()
        if not lifts:
            print("No lifts defined in knowledge base.", file=self.out)
            return 1
        print("Supported lifts:", file=self.out)
        for lift in lifts:
            phase_count = len(self.kb.phases_for(lift))
            print(f"  {lift}  ({phase_count} phases)", file=self.out)
        return 0


@dataclass
class PhasesCommand:
    kb: KnowledgeBase
    lift: str
    out: IO[str]

    def run(self) -> int:
        if not self.kb.has_lift(self.lift):
            print(f"Unknown lift: {self.lift}", file=self.out)
            return 1
        print(f"Phases for {self.lift}:", file=self.out)
        for phase, joints in self.kb.phases_for(self.lift).items():
            print(f"  {phase}  ({', '.join(joints.keys())})", file=self.out)
        return 0


@dataclass
class RulesCommand:
    kb: KnowledgeBase
    lift: str
    phase: str
    out: IO[str]

    def run(self) -> int:
        try:
            phase_enum = LiftPhase(self.phase)
        except ValueError:
            print(f"Unknown phase: {self.phase}", file=self.out)
            return 1

        rules = self.kb.rules_for(self.lift, phase_enum)
        if not rules:
            print(f"No rules defined for {self.lift}/{self.phase}", file=self.out)
            return 1

        print(f"Rules for {self.lift} → {self.phase}:", file=self.out)
        for joint, rule in rules.items():
            print(f"\n  {joint}  [{rule.priority.value}]", file=self.out)
            print(f"    good:    {rule.good[0]}–{rule.good[1]}°", file=self.out)
            print(f"    warning: {rule.warning[0]}–{rule.warning[1]}°", file=self.out)
            print(f"    fault:   {rule.fault[0]}–{rule.fault[1]}°", file=self.out)
            print(f"    cue:     {rule.feedback}", file=self.out)
        return 0


@dataclass
class ValidateCommand:
    video_path: str
    out: IO[str]

    def run(self) -> int:
        try:
            FileVideoValidator().validate(self.video_path)
        except ValueError as e:
            print(f"FAIL: {e}", file=self.out)
            return 1
        print(f"OK: {self.video_path} is a valid video", file=self.out)
        return 0


@dataclass
class AnalyzeCommand:
    use_case: _UseCase
    input_path: str
    output_path: str
    out: IO[str]

    def run(self) -> int:
        result = self.use_case.execute(self.input_path, self.output_path)
        if isinstance(result, AnalyzeVideoResult):
            print(f"Output written to: {result.output_path}", file=self.out)
            if result.report_json_path:
                print(f"JSON report: {result.report_json_path}", file=self.out)
            if result.report_summary_path:
                print(f"Summary report: {result.report_summary_path}", file=self.out)
            print("Session feedback:", file=self.out)
            for line in result.feedback_summary:
                print(f"  {line}", file=self.out)
        else:
            print(f"Output written to: {result}", file=self.out)
        return 0


@dataclass
class CompareCommand:
    use_case: _CompareUseCase
    left_path: str
    right_path: str
    output_path: str
    out: IO[str]

    def run(self) -> int:
        try:
            resolved = self.use_case.execute(self.left_path, self.right_path, self.output_path)
        except ValueError as e:
            print(f"FAIL: {e}", file=self.out)
            return 1
        print(f"Side-by-side written to: {resolved}", file=self.out)
        return 0
