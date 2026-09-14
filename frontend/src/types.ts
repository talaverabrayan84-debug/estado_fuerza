export type Role = 'admin' | 'capacitacion' | 'trabajador';
export type User = {id:string; rol:Role; personal_id:string|null; email:string};
export type Catalog = {id:string; nombre:string; activo:boolean};
export type Catalogs = {corporaciones:Catalog[]; cargos:Catalog[]; grados:Catalog[]};
export type Person = {personal_id:string; cuip:string|null; curp:string|null; nombre_completo:string; sexo:'H'|'M'|null; corporacion_id:string; corporacion:string; adscripcion:string; cargo_id:string|null; grado_id:string|null; cargo:string|null; grado:string|null; estatus:string; estatus_vigencia:string; dias_restantes:number|null; fecha_vencimiento:string|null; fecha_certificacion:string|null};
export type Evaluation = {id:string; personal_id:string; institucion_evaluadora:string; fecha_certificacion:string; fecha_vencimiento:string|null; resultado:string; folio:string; activo:boolean};
export const states = ['Vigente','Por vencer','Vencida','Sin registro','No aprobado'];
export const roleLabels:Record<Role,string> = {admin:'Administrador',capacitacion:'Gestor de capacitación',trabajador:'Trabajador'};
