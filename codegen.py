#!/usr/bin/env python3.11
from enum import Enum, auto
from typing import List
import tempfile,subprocess,os

class _RegMeta(type):
  _special = dict(
      SP="sp",
      LR="lr",
      FP="fp",
      XZR="xzr",
      WZR="wzr"
  )

  def __getattr__(cls, name):
    # Handle special registers
    if name in cls._special: return cls._special[name]

    # Handle Xn and Wn (0 <= n < 30)
    if name.startswith("X"):
      try:
        idx = int(name[1:])
        if 0 <= idx < 30:
          return f"x{idx}"
      except ValueError: pass

    if name.startswith("W"):
      try:
        idx = int(name[1:])
        if 0 <= idx < 30:
          return f"w{idx}"
      except ValueError: pass

    raise AttributeError(f"Register '{name}' is not defined.")

class Reg(metaclass=_RegMeta):
    @classmethod
    def X(cls, i): return f"x{i}" if 0 <= i < 30 else None
    @classmethod
    def W(cls, i): return f"w{i}" if 0 <= i < 30 else None


class Inst(Enum):
  # Data Movement Instructions
  MOV = auto()   # Move
  LDR = auto()   # Load Register
  STR = auto()   # Store Register
  STRB = auto()   # Store Register Byte
  STRH = auto()  # Store Register Harlfworld
  ADR = auto()   # Address of a Label
  ADRP = auto()  # Address of a Page
  MOVZ = auto()  # Move with zero
  MOVK = auto()  # Move Keep
  MOVN = auto()  # Move with Not

  # Arithmetic Instructions
  ADD = auto()
  SUB = auto()
  MUL = auto()
  UDIV = auto()
  NEG = auto()
  INC = auto()

  # Logical / Bitwise Instructions
  AND = auto()
  ORR = auto()
  EOR = auto()  # Logical Exclusive OR.
  MVN = auto()  # Move Not
  LSL = auto()  # Logical Shift Left
  LSR = auto()  # Logical Shift Right

  # Comparison & Test Instructions
  CMP = auto()  # Compare
  TST = auto()  # Test Bits
  CCMP = auto()  # Conditional Compare
  NOP = auto()  # No Operation
  SVC = auto()  # SuperVisor Call
  RET = auto()  # Return


class Instruction:
  def __init__(self, op: Inst, args):
    self.op = op
    self.args = args

  def emit(self):
    if self.op == Inst.MOV:
      dst, src = self.args
      return f"\t mov {dst}, #{src}" if isinstance(src, int) else f"\t mov {dst}, {src}"
    elif self.op == Inst.ADD:
      dst, src1, src2 = self.args
      return f"\t add {dst}, {src1}, {src2}"
    elif self.op == Inst.RET: return "\t ret"
    elif self.op == Inst.NOP: return "\t nop"
    elif self.op in [Inst.MOVK, Inst.MOVZ]:
      if len(self.args) == 2:
        dst, imm = self.args
        return f"\t {self.op.name.lower()} {dst}, #{imm}"
      elif len(self.args) == 4 and self.args[2] in ['LSL','LSR']:
        dst, imm, shift_type, shift = self.args
        shift_type_lower = shift_type.lower()
        assert self.op == Inst.MOVZ and shift_type == "LSL" and shift in [0,16,32,48], "Instruksi ini tidak sah !"
        return f"\t {self.op.name.lower()} {dst}, #{imm}, {shift_type_lower} #{shift}"
      else: raise ValueError( f"{self.op} expects 2 or 4 arguments, got {self.args}")
    elif self.op == Inst.SUB:
      dst, src = self.args
      return f"\t sub {dst}, {dst}, #{src}"
    elif self.op == Inst.SVC:
      dst = self.args[0]
      return f"\t svc #{dst}"
    elif self.op in [Inst.STR, Inst.STRB, Inst.STRH]:
      src, addr = self.args
      if isinstance(addr, list):
        if len(addr) == 1:
          base = addr[0]
          return f"\t {self.op.name.lower()} {src}, [{base}]"
        elif len(self.args) == 2:
          base, offset = addr
          return f"\t {self.op.name.lower()} {src}, [{base}, #{offset}]"
        else:
          raise ValueError(
              f"{self.op.name.lower()} instruction requires 2 or 3 arguments, got {len(self.args)}")
      else:
        raise ValueError(f"Unknown instruction: {self.op}")

class Codegen:
  def alloc_size(self, n_size: int): return (n_size + 15) & ~15

  def __init__(self):
    self.instructions: List[Instruction] = []

  def emit(self, inst: Instruction):
    self.instructions.append(inst)

  def __str__(self) -> str: return self.generate()

  def write(self,filename:str):
    with open(filename,"w") as f:
      f.write(self.generate())

  def generate(self) -> str:
    lines = [".section __TEXT,__text", ".global _main", "", "_main:"]
    for instr in self.instructions: lines.append(instr.emit())
    return "\n".join(lines)

  def run(self, asm_code: str = None):
    with tempfile.TemporaryDirectory() as tmpdir:
      exe_path = os.path.join(tmpdir,"a")
      self.compile(exe_path,asm_code=asm_code,write=False)
      result = subprocess.run([exe_path])
      print(f"\n[INFO] Return code: {result.returncode}")

  def compile(self,filename:str="a", asm_code:str=None,write:bool=True):
    asm_code = self.generate() if asm_code is None else asm_code
    dir = "build"
    if dir == "build": os.makedirs(dir, exist_ok=True)
    if not write: dir = filename
    try:
      asm_path = os.path.join(dir, f"{filename}.s")
      obj_path = os.path.join(dir, f"{filename}.o")
      exe_path = os.path.join(dir, filename)

      with open(asm_path,"w") as f: f.write(asm_code)

      # Compile dengan assembler
      subprocess.run(["as", "-o", obj_path, asm_path], check=True)

      # Link menjadi executable
      result = subprocess.run(
        [
          "ld", "-o", exe_path, obj_path,
          "-lSystem", "-syslibroot", "/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk",
          "-e", "_main"
        ],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=True, text=True
      )

      print(f"\n[INFO] Executable created: {exe_path}")
      if result.stdout:
        print("[stdout]:", result.stdout)
      if result.stderr:
        print("[stderr]:", result.stderr)
      if not write:return exe_path
    except subprocess.CalledProcessError as e:
      print(f"[ERROR] Compilation failed:\n{e.stderr}")
    except Exception as e:
      print(f"[ERROR] Unexpected error:\n{e}")
  
  def allocate_stack(self,n_size:int):
    n_size = self.alloc_size(n_size)
    self.instructions.append(Instruction(Inst.SUB,[Reg.SP,16]))
  
  def deallocate_stack(self,n_size):
    n_size = self.alloc_size(n_size)
    self.instructions.append(Instruction(Inst.ADD, [Reg.SP, Reg.SP, n_size]))
    
  def syscall_exit(self):
    # System call number untuk exit
    self.instructions.append(Instruction(Inst.MOV, [Reg.X16, 1]))
    # Status exit (0 = Success)
    self.instructions.append(Instruction(Inst.MOV, [Reg.X0, 0]))
    # Prefix untuk system call BSD
    self.instructions.append(Instruction(Inst.MOV, [Reg.X8, 0x2000000]))
    # Gabungkan: 0x2000001 untuk exit
    self.instructions.append(Instruction(Inst.ADD, [Reg.X16, Reg.X16, Reg.X8]))
    # Panggil kernel
    self.instructions.append(Instruction(Inst.SVC, [0]))

  def syscall_write(self, n_literal: int):
    # args1 : file descriptor 1 (stdout) 
    self.instructions.append(Instruction(Inst.MOV, [Reg.X0, 1]))                      
    # args2 : Menyetel x1 ke alamat buffer (di stack pointer)
    self.instructions.append(Instruction(Inst.MOV, [Reg.X1, Reg.SP]))                 
    # args3 : x2 adalah argumen ketiga syscall write, yaitu panjang data (dalam byte) yang akan ditulis.
    self.instructions.append(Instruction(Inst.MOV, [Reg.X2, n_literal]))              
    """
    Syscall number di macOS ARM64 disimpan di x16 dan dihitung:
    x16 = 4 + 0x2000000 ⟶ x16 = 0x2000004
    0x2000004 adalah syscall write di macOS.
    """
    self.instructions.append(Instruction(Inst.MOV, [Reg.X16, 4]))
    self.instructions.append(Instruction(Inst.MOV, [Reg.X8, 0x2000000]))
    self.instructions.append(Instruction(Inst.ADD, [Reg.X16, Reg.X16, Reg.X8]))

    # Supervisor Call
    self.instructions.append(Instruction(Inst.SVC, [0]))

class TemplateInstruction:
  @staticmethod
  def print_sum(a: int, b: int):
    cg = Codegen()
    c = str(a + b)
    cg.allocate_stack(len(c))
    for idx, val in enumerate(c):
      cg.emit(Instruction(Inst.MOVZ, [Reg.X1, ord(val), "LSL", 0]))
      cg.emit(Instruction(Inst.STRB, [Reg.W1, [Reg.SP, idx]]))
    cg.syscall_write(len(c))
    cg.deallocate_stack(len(c))
    cg.syscall_exit()
    return cg
  
  @staticmethod
  def print_str(text:str):
    cg = Codegen()
    n_literal = len(text)
    cg.allocate_stack(n_literal)

    # Memasukkan karakter ASCII satu per satu ke stack
    for idx, val in enumerate(text):
      cg.emit(Instruction(Inst.MOV, [Reg.W1, ord(val)]))
      cg.emit(Instruction(Inst.STRB, [Reg.W1, [Reg.SP, idx]]))
    cg.syscall_write(n_literal)
    cg.deallocate_stack(n_literal)
    cg.syscall_exit()
    return cg

if __name__ == "__main__":
  text = """
    Lorem Ipsum is simply dummy text of the printing and 
    typesetting industry. Lorem Ipsum has been the industry's
    standard dummy text ever since the 1500s, when an unknown
    printer took a galley of type and scrambled it to make a type
    specimen book. It has survived not only five centuries,
    but also the leap into electronic typesetting, remaining
    essentially unchanged. It was popularised in the 1960s with
    the release of Letraset sheets containing Lorem Ipsum passages,
    and more recently with desktop publishing software like Aldus PageMaker
    including versions of Lorem Ipsum.\n
    """
  cg = TemplateInstruction.print_str(text)
  cg.compile()
