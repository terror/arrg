import typing as t


def infer_default_value(field_type: t.Callable) -> t.Any:
  match field_type:
    case _ if field_type is bool:
      return False
    case _ if field_type is int:
      return 0
    case _ if field_type is float:
      return 0.0
    case _ if field_type is str:
      return ''
    case _ if field_type is list or t.get_origin(field_type) is list:
      return []
    case _ if field_type is tuple:
      return ()
    case _ if t.get_origin(field_type) is t.Union:
      return infer_default_value(resolve_type(field_type))
    case _:
      return None


def resolve_type(field_type: t.Any) -> t.Callable:
  match field_type:
    case _ if t.get_origin(field_type) is list:
      args = t.get_args(field_type)

      if args and args[0] != t.Any:
        return resolve_type(args[0])

      return str

    case _ if t.get_origin(field_type) is t.Union:
      args = t.get_args(field_type)

      if args:
        non_none_args = [arg for arg in args if arg is not type(None)]

        if (
          non_none_args
          and len(non_none_args) > 1
          and any(t in non_none_args for t in [int, str, float, bool])
        ):

          def union_converter(value):
            for arg_type in non_none_args:
              try:
                if arg_type is bool:
                  if value.lower() in ('true', 't', 'yes', 'y', '1'):
                    return True
                  elif value.lower() in ('false', 'f', 'no', 'n', '0'):
                    return False
                  continue
                return arg_type(value)
              except (ValueError, TypeError):
                continue
            return str(value)

          return union_converter

        return resolve_type(non_none_args[0])

      return str

    case type() as cls:
      return cls

    case _ if field_type is bool:
      return bool

    case _ if field_type is int:
      return int

    case _ if field_type is float:
      return float

    case _ if field_type is tuple:
      return tuple

    case _:
      return str
