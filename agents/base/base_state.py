from typing import Any, Dict, Generic, List, TypeVar, get_origin, get_args, TypedDict, Annotated
from utils.logs.logging_utils import logger

GenericAgentState = TypeVar('GenericAgentState', bound=Any)


class BaseState(Generic[GenericAgentState]):
    """
    Base class to handle field classifications and provide utility methods.
    
    Field classifications:
    - @in: Indicates that the field is used for input information only and should not be modified during processing.
    - @out: Indicates that the field is used to store results and is updated as processing progresses.
    - @inout: Indicates that the field is used both for input information and for storing results.
    - @internal: Indicates that the field is part of the persisted state and is used internally for decision-making or holding necessary information during processing.
    """
    
    _in_: str = "@in"
    _out_: str = "@out"
    _inout_: str = "@inout"
    _internal_: str = "@internal"
    
    def __init__(self, cls: GenericAgentState):
        """
        Initialize with a TypedDict class to classify fields.

        :param cls: The TypedDict class whose fields need to be classified.
        """
        self.cls = cls
        self.class_name = cls.__name__
        logger.debug(f"Initializing State for class: {self.class_name}")

        # Extract annotations
        extractor = AnnotationExtractor(cls)
        annotations = extractor.extract()

        # Classify fields
        classifier = FieldClassifier(annotations)
        classifications = {
            '_in_': self._in_,
            '_out_': self._out_,
            '_inout_': self._inout_,
            '_internal_': self._internal_
        }
        classifier.classify(classifications)

        # Assign classified fields
        self._fields = classifier.fields
        self._in_fields = classifier.in_fields
        self._out_fields = classifier.out_fields
        self._inout_fields = classifier.inout_fields
        self._internal_fields = classifier.internal_fields

    # Classification methods remain unchanged
    @classmethod
    def in_field(cls, description: str = "") -> str:
        return f"{cls._in_} {description}"

    @classmethod
    def out_field(cls, description: str = "") -> str:
        return f"{cls._out_} {description}"
    
    @classmethod
    def inout_field(cls, description: str = "") -> str:
        return f"{cls._inout_} {description}"
    
    @classmethod
    def internal_field(cls, description: str = "") -> str:
        return f"{cls._internal_} {description}"

    # Accessor methods remain unchanged
    def get_fields(self) -> List[str]:
        return self._fields
    
    def get_in_fields(self) -> List[str]:
        return self._in_fields

    def get_out_fields(self) -> List[str]:
        return self._out_fields

    def get_inout_fields(self) -> List[str]:
        return self._inout_fields
    
    def get_internal_fields(self) -> List[str]:
        return self._internal_fields

    def print_field_classifications(self):
        """
        Print field classifications in a clear and organized manner, including counts for each category.
        """
        print(f"=== Field Classifications for {self.class_name} ===\n")
        
        # Define categories and their corresponding methods
        categories = {
            "All Fields": self.get_fields(),
            "@in Fields": self.get_in_fields(),
            "@out Fields": self.get_out_fields(),
            "@inout Fields": self.get_inout_fields(),
            "@internal Fields": self.get_internal_fields()
        }
        
        # Iterate through each category and print the fields with counts
        for category_name, fields in categories.items():
            print(f"{category_name} ({len(fields)}):")
            print("-" * len(category_name))
            for field in fields:
                print(f"  - {field}")
            print("\n")


class FieldClassifier:
    """
    Responsible for classifying fields based on their annotations.
    """
    def __init__(self, annotations: Dict[str, str]):
        self.annotations = annotations
        self._in_fields = []
        self._out_fields = []
        self._inout_fields = []
        self._internal_fields = []
        self._fields = []
        logger.debug("Initializing FieldClassifier.")

    def classify(self, classifications: Dict[str, str]):
        for field_name, annotation in self.annotations.items():
            if annotation.startswith(classifications['_internal_']):
                self._internal_fields.append(field_name)
                self._fields.append(field_name)
                logger.debug(f"Classified field '{field_name}' as '@internal'")
            else:
                self._fields.append(field_name)
                if annotation.startswith(classifications['_inout_']):
                    self._in_fields.append(field_name)
                    self._out_fields.append(field_name)
                    self._inout_fields.append(field_name)
                    logger.debug(f"Classified field '{field_name}' as '@inout'")
                elif annotation.startswith(classifications['_in_']):
                    self._in_fields.append(field_name)
                    logger.debug(f"Classified field '{field_name}' as '@in'")
                elif annotation.startswith(classifications['_out_']):
                    self._out_fields.append(field_name)
                    logger.debug(f"Classified field '{field_name}' as '@out'")
                else:
                    logger.error(f"Field '{field_name}' has an unrecognized annotation '{annotation}'.")
                    raise ValueError(f"Unrecognized annotation '{annotation}' for field '{field_name}'.")

    @property
    def in_fields(self) -> List[str]:
        return self._in_fields

    @property
    def out_fields(self) -> List[str]:
        return self._out_fields

    @property
    def inout_fields(self) -> List[str]:
        return self._inout_fields

    @property
    def internal_fields(self) -> List[str]:
        return self._internal_fields

    @property
    def fields(self) -> List[str]:
        return self._fields


class AnnotationExtractor:
    """
    Responsible for extracting annotations from a TypedDict.
    """
    def __init__(self, cls: GenericAgentState):
        self.cls = cls
        self.class_name = cls.__name__
        logger.debug(f"Initializing AnnotationExtractor for class: {self.class_name}")

    def extract(self) -> Dict[str, str]:
        annotations = {}
        type_hints = getattr(self.cls, '__annotations__', {})
        logger.debug(f"Extracting annotations for class: {self.class_name}")
        for field_name, field_type in type_hints.items():
            annotation = None
            if get_origin(field_type) is Annotated:
                args = get_args(field_type)
                if len(args) > 1 and isinstance(args[1], str):
                    annotation = args[1]
            elif hasattr(field_type, '__metadata__'):
                metadata = field_type.__metadata__
                if metadata and isinstance(metadata[0], str):
                    annotation = metadata[0]
            if annotation:
                annotations[field_name] = annotation
                logger.debug(f"Field '{field_name}' annotated as '{annotation}'")
            else:
                logger.warning(f"Field '{field_name}' has no valid annotation.")
        return annotations
