"""Build a portable, local-only demo scene around a generated robot package."""
import argparse
from pathlib import Path
from pxr import Usd,UsdGeom,UsdPhysics,UsdLux,Gf,Sdf
ap=argparse.ArgumentParser();ap.add_argument('folder',type=Path);a=ap.parse_args();path=a.folder/'demo.usda'
s=Usd.Stage.CreateNew(str(path)) if not path.exists() else Usd.Stage.Open(str(path));s.GetRootLayer().Clear()
world=UsdGeom.Xform.Define(s,'/World');s.SetDefaultPrim(world.GetPrim());UsdGeom.SetStageMetersPerUnit(s,1);UsdGeom.SetStageUpAxis(s,'Z')
scene=UsdPhysics.Scene.Define(s,'/World/PhysicsScene');scene.CreateGravityDirectionAttr(Gf.Vec3f(0,0,-1));scene.CreateGravityMagnitudeAttr(9.81)
scene.GetPrim().AddAppliedSchema('PhysxSceneAPI');scene.GetPrim().CreateAttribute('physxScene:timeStepsPerSecond',Sdf.ValueTypeNames.UInt,custom=False).Set(240)
scene.GetPrim().CreateAttribute('physxScene:solverType',Sdf.ValueTypeNames.Token,custom=False).Set('TGS')
robot=s.DefinePrim('/World/Robot','Xform');robot.GetReferences().AddReference('r1pro_2026.usd')
translate=robot.GetAttribute('xformOp:translate')
if not translate:translate=UsdGeom.Xformable(robot).AddTranslateOp().GetAttr()
translate.Set(Gf.Vec3d(0,0,.015))
ground=UsdGeom.Mesh.Define(s,'/World/Ground');ground.CreatePointsAttr([(-10,-10,0),(10,-10,0),(10,10,0),(-10,10,0)])
ground.CreateFaceVertexCountsAttr([4]);ground.CreateFaceVertexIndicesAttr([0,1,2,3]);ground.CreateSubdivisionSchemeAttr('none');ground.CreateDisplayColorAttr([(.35,.35,.35)]);UsdPhysics.CollisionAPI.Apply(ground.GetPrim())
UsdLux.DomeLight.Define(s,'/World/DomeLight').CreateIntensityAttr(600)
sun=UsdLux.DistantLight.Define(s,'/World/DistantLight');sun.CreateIntensityAttr(1800);UsdGeom.Xformable(sun).AddRotateXYZOp().Set(Gf.Vec3f(-35,25,25))
cam=UsdGeom.Camera.Define(s,'/World/Camera');cam.CreateFocalLengthAttr(35);cam.CreateHorizontalApertureAttr(36);cam.CreateVerticalApertureAttr(27);cam.CreateClippingRangeAttr(Gf.Vec2f(.01,100))
UsdGeom.Xformable(cam).AddTransformOp().Set(Gf.Matrix4d().SetLookAt(Gf.Vec3d(3,2,2),Gf.Vec3d(0,0,.85),Gf.Vec3d(0,0,1)).GetInverse())
s.GetRootLayer().Save();print(path)
