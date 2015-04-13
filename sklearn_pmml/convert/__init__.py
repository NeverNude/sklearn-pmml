from pyxb.utils.domutils import BindingDOMSupport as bds

from sklearn_pmml import pmml
from sklearn_pmml.convert.features import Feature, NumericFeature, CategoricalFeature, RealNumericFeature


__all__ = ['TransformationContext', 'EstimatorConverter', 'find_converter']

estimator_to_converter = {}


class TransformationContext(object):
    """
    Context holder object
    """

    def __init__(self, **schemas):
        self.schemas = schemas


class EstimatorConverter(object):
    """
    A new base class for the estimator converters
    """
    PMML_VERSION = "4.2"

    MODE_CLASSIFICATION = 'classification'
    MODE_REGRESSION = 'regression'
    all_modes = {
        MODE_CLASSIFICATION,
        MODE_REGRESSION
    }

    SCHEMA_INPUT = 'input'
    SCHEMA_NUMERIC = 'numeric'
    SCHEMA_OUTPUT = 'output'

    def __init__(self, estimator, context, mode):
        self.model_function_name = mode
        self.estimator = estimator
        self.context = context

        assert mode in self.all_modes, 'Unknown mode {}. Supported modes: {}'.format(mode, self.all_modes)

    def data_dictionary(self):
        """
        Build a data dictionary and return a DataDictionary element
        """
        dd = pmml.DataDictionary()
        for f in self.context.schemas[self.SCHEMA_INPUT] + self.context.schemas[self.SCHEMA_INPUT]:
            data_field = pmml.DataField(dataType=f.data_type, name=f.name, optype=f.optype)
            dd.DataField.append(data_field)
            if isinstance(f, CategoricalFeature):
                for v in enumerate(f.value_list):
                    data_field.append(pmml.Value(value_=v))
        return dd

    def transformation_dictionary(self):
        """
        Build a transformation dictionary and return a TransformationDictionary element
        """
        td = pmml.TransformationDictionary()
        encoded_schema = []
        self.context.schemas[self.SCHEMA_NUMERIC] = encoded_schema

        for f in self.context.schemas[self.SCHEMA_INPUT]:
            if isinstance(f, CategoricalFeature):
                ef = RealNumericFeature(name=f.name, namespace=self.SCHEMA_NUMERIC)
                df = pmml.DerivedField(
                    name=ef.full_name,
                    optype=ef.optype,
                    dataType=ef.data_type
                )
                mv = pmml.MapValues(outputColumn='output', dataType=ef.data_type)
                mv.append(pmml.FieldColumnPair(field=f.full_name, column='input'))
                it = pmml.InlineTable()
                for i, v in enumerate(f.value_list):
                    r = pmml.row()
                    input = bds().createChildElement('input')
                    bds().appendTextChild(v, input)
                    output = bds().createChildElement('output')
                    bds().appendTextChild(i, output)
                    r.append(input)
                    r.append(output)
                    it.append(r)
                td.append(df.append(mv.append(it)))
            else:
                ef = RealNumericFeature(name=f.name)

            encoded_schema.append(ef)
        assert len(encoded_schema) == len(self.context.schemas[self.SCHEMA_INPUT])
        return td

    def model(self):
        """
        Build a mining model and return one of the MODEL-ELEMENTs
        """
        pass

    def mining_schema(self):
        """
        Build a mining schema and return MiningSchema element
        """
        ms = pmml.MiningSchema()

        for f in self.context.schemas[self.SCHEMA_INPUT]:
            ms.append(pmml.MiningField(invalidValueTreatment=f.invalid_value_treatment, name=f.name))

        for f in self.context.schemas[self.SCHEMA_OUTPUT]:
            ms.append(pmml.MiningField(
                name=f.full_name,
                usageType="predicted"
            ))
        return ms

    def header(self):
        """
        Build and return Header element
        """
        return pmml.Header()

    def pmml(self):
        """
        Build PMML from the context and estimator.
        Returns PMML element
        """
        p = pmml.PMML(version="4.2")
        p.append(self.header())
        p.append(self.data_dictionary())
        p.append(self.transformation_dictionary())
        p.append(self.model())
        return p


def find_converter(estimator):
    # TODO: do the search here
    return estimator_to_converter.get(estimator.__class__, None)
