#!/usr/bin/env python3.11
from enum import Enum, auto
from typing import List, Union
import os,tempfile,subprocess

class Reg:
    """
        Register wN ->  32 bits
        Register xN ->  64 bits

    """
    def __init__(self):
        for key in range(10):
            setattr(self, f"X{key}",f"x{key}" )
            setattr(self, f"W{key}",f"w{key}")

class Inst(Enum):
    # Data Movement Instructions
    MOV = auto(); LDR = auto(); STR = auto(); ADR = auto(); ADRP = auto();
    # Arithmetic Instructions
    ADD = auto(); SUB = auto(); MUL = auto(); UDIV = auto(); NEG = auto(); INC = auto();
    # Logical / Bitwise Instructions
    AND = auto(); ORR = auto(); EOR = auto(); MVN = auto(); LSL = auto(); LSR = auto();
    # Comparison & Test Instructions
    CMP = auto(); TST = auto(); CCMP = auto();

    NOP = auto(); SVC = auto(); RET = auto();

class Instruction:
    def __init__(self, op: Inst, args: List[Union[Reg, int]]):
        self.op = op
        self.args = args

    def emit(self) -> str:
        if self.op == Inst.MOV:
            dst, src = self.args
            return f"    mov {dst}, #{src}" if isinstance(src, int) else f"    mov {dst}, {src}"
        elif self.op == Inst.ADD:
            dst, src1, src2 = self.args
            return f"    add {dst}, {src1}, {src2}"
        elif self.op == Inst.RET:
            return "    ret"
        else:
            raise ValueError(f"Unknown instruction: {self.op}")

class Codegen:
    def __init__(self):
        self.instructions: List[Instruction] = []

    def emit(self, inst: Instruction):
        self.instructions.append(inst)

    def generate(self) -> str:
        lines = [".section __TEXT,__text", ".global _main", "", "_main:"]
        for instr in self.instructions:
            lines.append(instr.emit())
        return "\n".join(lines)

    def running(self):
        asm_code = self.generate()
        with tempfile.TemporaryDirectory() as tmpdir:
            asm_path = os.path.join(tmpdir, "program.s")
            obj_path = os.path.join(tmpdir, "program.o")
            exe_path = os.path.join(tmpdir, "program")
            with open(asm_path,"w") as f:
                f.write(asm_code)
            subprocess.run(["as","-o",obj_path,asm_path],check=True)
            subprocess.run([
                "ld", "-o", exe_path, obj_path,
                "-lSystem", "-syslibroot", "/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk",
                "-e", "_main"
            ], check=True)
            result = subprocess.run([exe_path])
            print(f"\n[INFO] Return code: {result.returncode}")


cg = Codegen()
Reg = Reg()
cg.emit(Instruction(Inst.MOV, [Reg.X0, 0x10]))
cg.emit(Instruction(Inst.MOV, [Reg.X1, 20]))
cg.emit(Instruction(Inst.ADD, [Reg.X2, Reg.X0, Reg.X1]))
cg.emit(Instruction(Inst.MOV, [Reg.X0, Reg.X2]))
cg.emit(Instruction(Inst.RET, []))

print(cg.generate())
cg.running()




    


